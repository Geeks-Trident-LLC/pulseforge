"""Envelope/body split (SPEC.md §2).

Detection order: known-format regex bank (patterns.yaml) first, since it's
free; an LLM-proposed split regex only on a shape none of those match,
cached afterward the same way naming/cache.py caches category resolutions
so a given source only ever pays that cost once per distinct envelope
shape. This module only implements the regex-bank half (SPEC.md §2.2 step
1) -- the LLM fallback (step 2) and confirm/persist (§2.3) are separate
concerns, not yet built (and deliberately deferred as a later add-on, not
guessed at ahead of need); NoMatchingPatternError is what a future caller
catches to know it's time to fall back.
"""

from __future__ import annotations

import dataclasses
import itertools
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import yaml

_PATTERNS_PATH = Path(__file__).parent / "patterns.yaml"


class NoMatchingPatternError(ValueError):
    """Raised by split_envelope when no entry in the regex bank matches.

    Not a bug to catch-and-ignore -- per SPEC.md §2.2, this is exactly
    the signal a caller uses to fall back to the LLM path instead of
    misparsing a line a known pattern was never meant to cover.

    Also raised by detect_format when scoring a sample against every
    known pattern doesn't land on exactly one confident answer -- the
    same signal, same meaning: known patterns didn't settle it, time to
    fall back.
    """


class DuplicatePatternNameError(ValueError):
    """Raised when patterns.yaml has two entries with the same name.

    A copy-pasted "name:" typo wouldn't otherwise be caught: patterns.yaml
    is a list, not a mapping, so YAML itself won't reject or silently drop
    either entry -- both stay in _KNOWN_PATTERNS, and the second is simply
    unreachable (split_envelope returns on the first match), not an error,
    until this check catches it at load time instead.
    """


@dataclass(frozen=True)
class EnvelopeSplit:
    format: str
    timestamp: str
    marker: str | None
    body: str
    raw: str
    # Position within a detect_format() sample -- None for a standalone
    # split_envelope() call, which has no batch/sample context to number.
    index: int | None = None


@dataclass(frozen=True)
class UnknownEnvelopeSplit:
    """A sample line that failed to parse against the source's detected
    format -- kept, not discarded, so a human can review exactly which
    lines a match-rate threshold's failure allowance actually covers
    before trusting the detection, instead of just trusting a bare
    percentage (SPEC.md §2.3's "a preview, not a label" principle,
    applied to the failures too, not just the successes).

    Always arises from a batch/sample context (detect_format()'s
    per-pattern scoring pass) -- unlike EnvelopeSplit.index, there's no
    standalone case where this index wouldn't be meaningful, so it's
    required, not optional.
    """

    index: int
    raw: str
    attempted_format: str
    reason: str


@dataclass(frozen=True)
class FormatDetectionResult:
    """A source's auto-detected format (SPEC.md §2.2 step 1), plus the
    evidence behind it -- callers deciding whether to trust an
    auto-detection (or show it to a user per §2.3) need the actual
    per-line results, not just a match-rate number.

    results is every sample line's outcome, in original sample order --
    the single source of truth for adjacency (see previous_result() /
    next_result()). envelope_splits/unknown_splits are filtered views
    over the same list, not separate data, so splitting a line into
    "success" or "failure" never loses its position relative to its
    neighbors the way two independently-built lists would.
    """

    format: str
    sample_size: int
    matched: int
    match_rate: float
    results: list[EnvelopeSplit | UnknownEnvelopeSplit]

    @property
    def envelope_splits(self) -> list[EnvelopeSplit]:
        return [r for r in self.results if isinstance(r, EnvelopeSplit)]

    @property
    def unknown_splits(self) -> list[UnknownEnvelopeSplit]:
        return [r for r in self.results if isinstance(r, UnknownEnvelopeSplit)]

    def previous_result(
        self, index: int
    ) -> EnvelopeSplit | UnknownEnvelopeSplit | None:
        """The result immediately before ``index`` in original sample
        order -- may be either an EnvelopeSplit or an UnknownEnvelopeSplit,
        regardless of which one ``index`` itself is. None if there isn't
        one (index is first, or out of bounds).
        """
        prev_index = index - 1
        if 0 <= prev_index < len(self.results):
            return self.results[prev_index]
        return None

    def next_result(self, index: int) -> EnvelopeSplit | UnknownEnvelopeSplit | None:
        """The result immediately after ``index`` in original sample
        order. None if there isn't one (index is last, or out of bounds).
        """
        next_index = index + 1
        if 0 <= next_index < len(self.results):
            return self.results[next_index]
        return None


def load_known_patterns() -> list[tuple[str, re.Pattern[str]]]:
    """Load and compile every entry in patterns.yaml, in file order --
    the order they're tried in split_envelope().

    Every pattern is compiled with:
    - re.VERBOSE: patterns.yaml writes a readable, commented, multi-line
      regex instead of one long line -- see its own header comment for
      the whitespace/escaping conventions that requires.
    - re.ASCII: RFC 5424's DIGIT is strictly ASCII 0-9; \\d without
      re.ASCII also matches non-ASCII Unicode decimal digits -- Arabic-
      Indic, Devanagari, etc. -- which would silently accept a line RFC
      5424 doesn't.
    - re.DOTALL: MSG's trailing ``.*`` otherwise can't span an embedded
      newline (Python's ``.`` excludes ``\\n`` by default) -- exactly
      what reassemble.py's multi-line entries need MSG to hold. Nothing
      else in the pattern uses a bare ``.``, so this only changes MSG's
      behavior, not HOSTNAME/APP-NAME/etc.'s explicit character classes.
    """
    entries = yaml.safe_load(_PATTERNS_PATH.read_text(encoding="utf-8")) or []
    seen: set[str] = set()
    patterns: list[tuple[str, re.Pattern[str]]] = []
    for entry in entries:
        name = entry["name"]
        if name in seen:
            raise DuplicatePatternNameError(
                f"duplicate pattern name {name!r} in patterns.yaml"
            )
        seen.add(name)
        if entry.get("pattern"):
            flags = re.VERBOSE | re.ASCII | re.DOTALL
            patterns.append((name, re.compile(entry["pattern"], flags)))
    return patterns


_KNOWN_PATTERNS = load_known_patterns()


def split_envelope(line: str) -> EnvelopeSplit:
    raw = line
    stripped = line.rstrip("\r\n")
    for name, pattern in _KNOWN_PATTERNS:
        match = pattern.match(stripped)
        if match is None:
            continue
        if name == "rfc5424-syslog":
            return _from_rfc5424(name, match.groupdict(), raw)
        raise NoMatchingPatternError(f"no field extractor registered for {name!r}")
    raise NoMatchingPatternError(f"no known envelope pattern matched: {stripped!r}")


def detect_format(
    lines: Iterable[str],
    *,
    sample_size: int = 100,
    match_rate_threshold: float = 0.99,
) -> FormatDetectionResult:
    """Auto-detect a source's envelope format (SPEC.md §2.2 step 1):
    take up to sample_size lines, parse every line against each known
    pattern, and return the one pattern whose match rate clears
    match_rate_threshold -- along with every line's actual result
    (EnvelopeSplit on success, UnknownEnvelopeSplit on failure), not just
    the aggregate numbers.

    Raises NoMatchingPatternError -- the same signal split_envelope()
    uses -- if zero patterns clear the bar (nothing confidently
    recognized) or more than one does (ambiguous). Either way, that's the
    point where a caller falls back to the LLM path (§2.2 step 2), not
    something this function decides on its own.

    Only reads the first sample_size lines from ``lines`` -- a caller
    wanting a spread-out sample (rather than a file's first N lines)
    controls that by what iterable it passes in, not by an option here.
    """
    sample = list(itertools.islice(lines, sample_size))
    if not sample:
        raise NoMatchingPatternError("no lines to sample -- source is empty")

    candidates = []
    for name, pattern in _KNOWN_PATTERNS:
        results = _parse_sample_against_pattern(name, pattern, sample)
        matched = sum(1 for r in results if isinstance(r, EnvelopeSplit))
        rate = matched / len(sample)
        if rate >= match_rate_threshold:
            candidates.append(
                FormatDetectionResult(name, len(sample), matched, rate, results)
            )

    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise NoMatchingPatternError(
            f"no known pattern cleared the {match_rate_threshold:.0%} match-rate "
            f"bar across {len(sample)} sample line(s)"
        )
    names = ", ".join(c.format for c in candidates)
    raise NoMatchingPatternError(
        f"ambiguous: {len(candidates)} known patterns each cleared the "
        f"{match_rate_threshold:.0%} bar ({names}) -- can't pick one automatically"
    )


def _parse_sample_against_pattern(
    name: str, pattern: re.Pattern[str], sample: list[str]
) -> list[EnvelopeSplit | UnknownEnvelopeSplit]:
    """Parse every line in sample against one specific named pattern,
    tagging each result with its position -- used only by detect_format(),
    once a single winning pattern has already been chosen for the whole
    source. Unlike split_envelope(), this never falls through to trying a
    different pattern: a line that fails against the source's own
    detected format is exactly what becomes an UnknownEnvelopeSplit, not
    a candidate for some other pattern to silently claim instead.
    """
    results: list[EnvelopeSplit | UnknownEnvelopeSplit] = []
    for i, line in enumerate(sample):
        stripped = line.rstrip("\r\n")
        match = pattern.match(stripped)
        if match is None:
            results.append(
                UnknownEnvelopeSplit(
                    index=i,
                    raw=line,
                    attempted_format=name,
                    reason=f"line does not match {name!r}",
                )
            )
            continue
        try:
            if name != "rfc5424-syslog":
                raise NoMatchingPatternError(
                    f"no field extractor registered for {name!r}"
                )
            parsed = _from_rfc5424(name, match.groupdict(), line)
        except NoMatchingPatternError as exc:
            results.append(
                UnknownEnvelopeSplit(
                    index=i, raw=line, attempted_format=name, reason=str(exc)
                )
            )
            continue
        results.append(dataclasses.replace(parsed, index=i))
    return results


def _from_rfc5424(name: str, fields: dict[str, str | None], raw: str) -> EnvelopeSplit:
    pri = int(fields["pri"])  # type: ignore[arg-type]
    if not 0 <= pri <= 191:
        raise NoMatchingPatternError(f"PRI {pri} out of RFC 5424's 0-191 range")
    if fields["version"] != "1":
        raise NoMatchingPatternError(
            f"unrecognized syslog VERSION {fields['version']!r} (only \"1\" is defined)"
        )

    marker = (
        f"<{fields['pri']}> {fields['hostname']} "
        f"{fields['app_name']}[{fields['proc_id']}] {fields['msg_id']}"
    )
    if fields["structured_data"] != "-":
        marker += f" {fields['structured_data']}"

    return EnvelopeSplit(
        format=name,
        timestamp=fields["timestamp"],  # type: ignore[arg-type]
        marker=marker,
        body=fields["msg"] or "",
        raw=raw,
    )
