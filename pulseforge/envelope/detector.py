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

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

_PATTERNS_PATH = Path(__file__).parent / "patterns.yaml"


class NoMatchingPatternError(ValueError):
    """Raised by split_envelope when no entry in the regex bank matches.

    Not a bug to catch-and-ignore -- per SPEC.md §2.2, this is exactly
    the signal a caller uses to fall back to the LLM path instead of
    misparsing a line a known pattern was never meant to cover.
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
