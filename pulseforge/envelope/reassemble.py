"""Reassembles physical lines into logical log entries -- the sub-step
between ingestion and detection/splitting (SPEC.md §2) that a stack
trace, a banner-style message, or any other multi-physical-line single
log entry needs: a line that doesn't look like the start of a known
envelope is glued onto whichever entry is currently being built, instead
of being treated as its own separate (and unparseable) entry.

Only usable once a source's format has already been confirmed (e.g. via
detector.detect_format()) -- the boundary check is done against that ONE
specific pattern, not "any known pattern". Same reasoning as
detector._parse_sample_against_pattern() never falling through to a
different pattern: once a source is believed to be format X, a line that
fails against X is exactly what should become an UnknownEnvelopeSplit
later, not a candidate for some unrelated pattern to silently reclaim
here instead.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from .detector import load_known_patterns

_KNOWN_PATTERNS = dict(load_known_patterns())


def reassemble_lines(
    lines: Iterable[str],
    format_name: str,
    *,
    max_continuation_lines: int = 50,
) -> Iterator[str]:
    """Glue continuation lines onto the logical entry they belong to.

    A line matching format_name's own pattern starts a new logical entry;
    anything else is appended (newline-joined) to whichever entry is
    currently being built. A leading continuation line with nothing yet
    to attach to is still yielded on its own -- not discarded -- so it's
    still available for review afterward (it'll fail to parse against
    format_name and land in UnknownEnvelopeSplit, same as any other
    unrecognized line).

    max_continuation_lines caps how many continuation lines can glue onto
    one entry before it's force-flushed: if the source's format was
    misidentified, or something is genuinely wrong, nothing should be
    able to grow an unbounded blob just because no new boundary ever
    turns up. The forced flush doesn't lose data -- it just stops that
    one entry from growing further and starts a new one from the current
    line, the same as if a real boundary had been found there.

    Raises ValueError if format_name isn't a name load_known_patterns()
    actually returned -- a caller error, not a parsing one. This is a
    generator function, though: nothing here runs until the result is
    first iterated, so the error surfaces then, not at call time --
    calling reassemble_lines(lines, "bad-name") alone doesn't raise;
    list(reassemble_lines(lines, "bad-name")) does.
    """
    pattern = _KNOWN_PATTERNS.get(format_name)
    if pattern is None:
        raise ValueError(f"no known pattern registered for format {format_name!r}")

    buffer: list[str] = []
    for line in lines:
        stripped = line.rstrip("\r\n")
        if pattern.match(stripped) is not None:
            if buffer:
                yield "\n".join(buffer)
            buffer = [stripped]
        elif not buffer:
            buffer = [stripped]
        elif len(buffer) > max_continuation_lines:
            yield "\n".join(buffer)
            buffer = [stripped]
        else:
            buffer.append(stripped)
    if buffer:
        yield "\n".join(buffer)
