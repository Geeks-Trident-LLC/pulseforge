"""Envelope/body split (SPEC.md §2).

Detection order: known-format regex bank (patterns.yaml) first, since it's
free; an LLM-proposed split regex only on a shape none of those match,
cached afterward the same way naming/cache.py caches category resolutions
so a given source only ever pays that cost once per distinct envelope
shape. This module only implements the regex-bank half (SPEC.md §2.2 step
1) -- the LLM fallback (step 2) and confirm/persist (§2.3) are separate
concerns, not yet built; NoMatchingPatternError is what a future caller
catches to know it's time to fall back.
"""

from __future__ import annotations

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


@dataclass(frozen=True)
class FormatDetectionResult:
    """A source's auto-detected format (SPEC.md §2.2 step 1), plus the
    evidence behind it -- callers deciding whether to trust an
    auto-detection (or show it to a user per §2.3) need the numbers, not
    just the name.
    """

    format: str
    sample_size: int
    matched: int
    match_rate: float


def load_known_patterns() -> list[tuple[str, re.Pattern[str]]]:
    """Load and compile every entry in patterns.yaml, in file order --
    the order they're tried in split_envelope().

    Every pattern is compiled with re.VERBOSE (patterns.yaml writes a
    readable, commented, multi-line regex instead of one long line -- see
    its own header comment for the whitespace/escaping conventions that
    requires) and re.ASCII (RFC 5424's DIGIT is strictly ASCII 0-9; \\d
    without re.ASCII also matches non-ASCII Unicode decimal digits --
    Arabic-Indic, Devanagari, etc. -- which would silently accept a line
    RFC 5424 doesn't).
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
            patterns.append((name, re.compile(entry["pattern"], re.VERBOSE | re.ASCII)))
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
    match_rate_threshold: float = 0.95,
) -> FormatDetectionResult:
    """Auto-detect a source's envelope format (SPEC.md §2.2 step 1):
    take up to sample_size lines, score each known pattern independently
    by what fraction of the sample it successfully parses, and return the
    one pattern that clears match_rate_threshold.

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
        matched = sum(
            1 for line in sample if _matches_pattern(name, pattern, line.rstrip("\r\n"))
        )
        rate = matched / len(sample)
        if rate >= match_rate_threshold:
            candidates.append(FormatDetectionResult(name, len(sample), matched, rate))

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


def _matches_pattern(name: str, pattern: re.Pattern[str], stripped: str) -> bool:
    """Does this specific pattern successfully parse this line -- regex
    shape *and* that format's own semantic checks (e.g. RFC 5424's
    PRI/VERSION validation in _from_rfc5424)?

    Only used by detect_format()'s match-rate scoring, which doesn't care
    *why* a line fails, just whether it does. split_envelope() keeps its
    own inline logic instead of sharing this: there, a regex match that
    fails semantic validation is a specific, useful error worth
    surfacing immediately (SPEC.md §2.2 step 1's actual line-by-line
    parsing), not something to silently retry against the next pattern
    the way a genuine regex non-match should be.
    """
    match = pattern.match(stripped)
    if match is None:
        return False
    try:
        if name == "rfc5424-syslog":
            _from_rfc5424(name, match.groupdict(), stripped)
            return True
    except NoMatchingPatternError:
        return False
    return False


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
