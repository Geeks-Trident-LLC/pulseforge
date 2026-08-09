"""Tests for envelope/reassemble.py."""

from __future__ import annotations

import pytest

from pulseforge.envelope.detector import split_envelope
from pulseforge.envelope.reassemble import reassemble_lines

_ENTRY_1 = "<34>1 2003-10-11T22:14:15.003Z host su - ID47 - first entry"
_ENTRY_2 = "<34>1 2003-10-11T22:15:00.000Z host su - ID48 - second entry"
_ENTRY_3 = "<34>1 2003-10-11T22:16:00.000Z host su - ID49 - third entry"


def test_no_continuations_yields_lines_unchanged() -> None:
    lines = [_ENTRY_1, _ENTRY_2, _ENTRY_3]
    assert list(reassemble_lines(lines, "rfc5424-syslog")) == lines


def test_glues_continuation_lines_onto_preceding_entry() -> None:
    lines = [
        _ENTRY_1,
        "  at com.foo.Bar.method(Bar.java:123)",
        "  at com.foo.Baz.method(Baz.java:456)",
        _ENTRY_2,
    ]
    result = list(reassemble_lines(lines, "rfc5424-syslog"))
    assert result == [
        _ENTRY_1
        + "\n  at com.foo.Bar.method(Bar.java:123)"
        + "\n  at com.foo.Baz.method(Baz.java:456)",
        _ENTRY_2,
    ]


def test_leading_continuation_before_any_boundary_is_still_emitted() -> None:
    lines = ["truncated garbage from log rotation", _ENTRY_1]
    result = list(reassemble_lines(lines, "rfc5424-syslog"))
    assert result == ["truncated garbage from log rotation", _ENTRY_1]


def test_consecutive_leading_continuations_are_glued_together() -> None:
    # Can't distinguish "unrelated junk lines" from "one entry's
    # continuation lines" when there's no preceding boundary at all --
    # both look identical, so both get glued the same consistent way.
    lines = ["junk one", "junk two", _ENTRY_1]
    result = list(reassemble_lines(lines, "rfc5424-syslog"))
    assert result == ["junk one\njunk two", _ENTRY_1]


def test_end_of_stream_flushes_final_buffered_entry() -> None:
    lines = [_ENTRY_1, "trailing continuation with no entry after it"]
    result = list(reassemble_lines(lines, "rfc5424-syslog"))
    assert result == [_ENTRY_1 + "\ntrailing continuation with no entry after it"]


def test_empty_input_yields_nothing() -> None:
    assert list(reassemble_lines([], "rfc5424-syslog")) == []


def test_safety_valve_force_flushes_past_max_continuation_lines() -> None:
    lines = [_ENTRY_1] + [f"continuation {i}" for i in range(5)]
    result = list(reassemble_lines(lines, "rfc5424-syslog", max_continuation_lines=2))
    # entry + 2 continuations, force-flushed, then the remaining 3
    # continuations glued into their own group (no boundary line of their
    # own, so treated as a leading-continuation-style group same as any
    # other unattached run).
    assert result == [
        _ENTRY_1 + "\ncontinuation 0\ncontinuation 1",
        "continuation 2\ncontinuation 3\ncontinuation 4",
    ]


def test_unknown_format_name_raises() -> None:
    with pytest.raises(ValueError, match="no known pattern registered"):
        list(reassemble_lines([_ENTRY_1], "not-a-real-format"))


def test_reassembled_entry_parses_with_embedded_newline_in_body() -> None:
    """End-to-end: the whole point of reassembling is that split_envelope
    can then parse the glued result as one entry, with the continuation
    lines living inside its body.
    """
    lines = [
        _ENTRY_1,
        "  at com.foo.Bar.method(Bar.java:123)",
        _ENTRY_2,
    ]
    reassembled = list(reassemble_lines(lines, "rfc5424-syslog"))
    assert len(reassembled) == 2

    first = split_envelope(reassembled[0])
    assert first.body == "first entry\n  at com.foo.Bar.method(Bar.java:123)"

    second = split_envelope(reassembled[1])
    assert second.body == "second entry"
