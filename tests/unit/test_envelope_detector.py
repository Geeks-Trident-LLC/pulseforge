"""Tests for envelope/detector.py against RFC 5424's own canonical
examples (RFC 5424 §6.5), plus the malformed/edge cases that motivated
NoMatchingPatternError instead of silently misparsing.
"""

from __future__ import annotations

import pytest

from pulseforge.envelope.detector import (
    NoMatchingPatternError,
    load_known_patterns,
    split_envelope,
)


def test_load_known_patterns_has_rfc5424() -> None:
    patterns = load_known_patterns()
    names = [name for name, _ in patterns]
    assert names == ["rfc5424-syslog"]


def test_rfc5424_example_1_plain_message() -> None:
    line = (
        "<34>1 2003-10-11T22:14:15.003Z mymachine.example.com su - ID47 - "
        "'su root' failed for lonvick on /dev/pts/8"
    )
    result = split_envelope(line)
    assert result.format == "rfc5424-syslog"
    assert result.timestamp == "2003-10-11T22:14:15.003Z"
    assert result.marker == "<34> mymachine.example.com su[-] ID47"
    assert result.body == "'su root' failed for lonvick on /dev/pts/8"
    assert result.raw == line


def test_rfc5424_example_2_ip_hostname_and_offset_timestamp() -> None:
    line = (
        "<165>1 2003-08-24T05:14:15.000003-07:00 192.0.2.1 myproc 8710 - - "
        "%% It's time to make the do-nuts."
    )
    result = split_envelope(line)
    assert result.timestamp == "2003-08-24T05:14:15.000003-07:00"
    assert result.marker == "<165> 192.0.2.1 myproc[8710] -"
    assert result.body == "%% It's time to make the do-nuts."


def test_rfc5424_example_3_structured_data_and_message() -> None:
    line = (
        "<165>1 2003-10-11T22:14:15.003Z mymachine.example.com evntslog - ID47 "
        '[exampleSDID@32473 iut="3" eventSource="Application" eventID="1011"] '
        "An application event log entry..."
    )
    result = split_envelope(line)
    assert (
        result.marker == "<165> mymachine.example.com evntslog[-] ID47 "
        '[exampleSDID@32473 iut="3" eventSource="Application" eventID="1011"]'
    )
    assert result.body == "An application event log entry..."


def test_rfc5424_example_4_structured_data_only_no_message() -> None:
    line = (
        "<165>1 2003-10-11T22:14:15.003Z mymachine.example.com evntslog - ID47 "
        '[exampleSDID@32473 iut="3" eventSource="Application" eventID="1011"]'
        '[examplePriority@32473 class="high"]'
    )
    result = split_envelope(line)
    assert (
        result.marker == "<165> mymachine.example.com evntslog[-] ID47 "
        '[exampleSDID@32473 iut="3" eventSource="Application" eventID="1011"]'
        '[examplePriority@32473 class="high"]'
    )
    assert result.body == ""


def test_pri_out_of_range_raises() -> None:
    line = "<192>1 2003-10-11T22:14:15.003Z host app - - - msg"
    with pytest.raises(NoMatchingPatternError, match="out of RFC 5424's 0-191 range"):
        split_envelope(line)


def test_unrecognized_version_raises() -> None:
    line = "<34>2 2003-10-11T22:14:15.003Z host app - - - msg"
    with pytest.raises(NoMatchingPatternError, match="VERSION"):
        split_envelope(line)


def test_rfc3164_style_line_does_not_match() -> None:
    line = (
        "Aug  3 09:15:01.123: %LINK-3-UPDOWN: Interface GigabitEthernet1/0/24, "
        "changed state to down"
    )
    with pytest.raises(
        NoMatchingPatternError, match="no known envelope pattern matched"
    ):
        split_envelope(line)


def test_garbage_line_does_not_match() -> None:
    with pytest.raises(NoMatchingPatternError):
        split_envelope("this is not a syslog line at all")
