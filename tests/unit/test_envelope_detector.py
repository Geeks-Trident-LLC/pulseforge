"""Tests for envelope/detector.py against RFC 5424's own canonical
examples (RFC 5424 §6.5), plus the malformed/edge cases that motivated
NoMatchingPatternError instead of silently misparsing.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import pulseforge.envelope.detector as detector
from pulseforge.envelope.detector import (
    DuplicatePatternNameError,
    NoMatchingPatternError,
    detect_format,
    load_known_patterns,
    split_envelope,
)

_VALID_RFC5424_LINE = (
    "<34>1 2003-10-11T22:14:15.003Z mymachine.example.com su - ID47 - "
    "'su root' failed for lonvick on /dev/pts/8"
)
_GARBAGE_LINE = "this is not a syslog line at all"


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


def test_non_ascii_digits_do_not_match() -> None:
    """re.ASCII must be in effect -- RFC 5424's DIGIT is strictly ASCII
    0-9, but \\d without re.ASCII also matches non-ASCII Unicode decimal
    digits (verified separately: Arabic-Indic/Devanagari digit strings
    match a bare \\d{3} pattern by default). A PRI built from Arabic-Indic
    digits for "192" must not match here.
    """
    arabic_indic_192 = "١٩٢"
    line = f"<{arabic_indic_192}>1 2003-10-11T22:14:15.003Z host app - - - msg"
    with pytest.raises(NoMatchingPatternError):
        split_envelope(line)


def test_duplicate_pattern_name_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    duplicate_patterns = tmp_path / "patterns.yaml"
    duplicate_patterns.write_text(
        "- name: rfc5424-syslog\n"
        "  pattern: 'a'\n"
        "- name: rfc5424-syslog\n"
        "  pattern: 'b'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(detector, "_PATTERNS_PATH", duplicate_patterns)
    with pytest.raises(DuplicatePatternNameError, match="rfc5424-syslog"):
        load_known_patterns()


def test_detect_format_at_default_threshold() -> None:
    # 95/100 -- exactly clears the default 95% bar (>=, not >).
    sample = [_VALID_RFC5424_LINE] * 95 + [_GARBAGE_LINE] * 5
    result = detect_format(sample)
    assert result.format == "rfc5424-syslog"
    assert result.sample_size == 100
    assert result.matched == 95
    assert result.match_rate == pytest.approx(0.95)


def test_detect_format_below_default_threshold_raises() -> None:
    # 90/100 -- clears SPEC.md's illustrative "e.g. >=90%" but not our
    # actual 95% default; must not silently detect on a looser bar.
    sample = [_VALID_RFC5424_LINE] * 90 + [_GARBAGE_LINE] * 10
    with pytest.raises(NoMatchingPatternError, match="no known pattern cleared"):
        detect_format(sample)


def test_detect_format_custom_threshold_allows_lower_bar() -> None:
    sample = [_VALID_RFC5424_LINE] * 85 + [_GARBAGE_LINE] * 15
    result = detect_format(sample, match_rate_threshold=0.8)
    assert result.match_rate == pytest.approx(0.85)


def test_detect_format_empty_source_raises() -> None:
    with pytest.raises(NoMatchingPatternError, match="no lines to sample"):
        detect_format([])


def test_detect_format_only_samples_first_sample_size_lines() -> None:
    # 100 valid lines followed by 100 garbage lines: default sample_size
    # of 100 must only ever look at the valid prefix, never touch the
    # garbage tail, regardless of how many lines the source actually has.
    sample = [_VALID_RFC5424_LINE] * 100 + [_GARBAGE_LINE] * 100
    result = detect_format(sample)
    assert result.sample_size == 100
    assert result.matched == 100
    assert result.match_rate == pytest.approx(1.0)


def test_detect_format_respects_smaller_custom_sample_size() -> None:
    sample = [_VALID_RFC5424_LINE] * 10 + [_GARBAGE_LINE] * 90
    result = detect_format(sample, sample_size=10)
    assert result.sample_size == 10
    assert result.matched == 10


def test_detect_format_ambiguous_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Not reachable with patterns.yaml's real single entry -- exercises
    the ambiguous branch directly by faking two patterns that both
    "match" every sample line, standing in for two real formats whose
    regex banks both happen to clear the bar on the same source.
    """
    fake_patterns = [("fake-a", re.compile(".*")), ("fake-b", re.compile(".*"))]
    monkeypatch.setattr(detector, "_KNOWN_PATTERNS", fake_patterns)
    monkeypatch.setattr(
        detector, "_matches_pattern", lambda name, pattern, stripped: True
    )
    with pytest.raises(NoMatchingPatternError, match="ambiguous"):
        detect_format(["anything"] * 10)
