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
    EnvelopeSplit,
    NoMatchingPatternError,
    UnknownEnvelopeSplit,
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
    # 99/100 -- exactly clears the default 99% bar (>=, not >).
    sample = [_VALID_RFC5424_LINE] * 99 + [_GARBAGE_LINE] * 1
    result = detect_format(sample)
    assert result.format == "rfc5424-syslog"
    assert result.sample_size == 100
    assert result.matched == 99
    assert result.match_rate == pytest.approx(0.99)


def test_detect_format_below_default_threshold_raises() -> None:
    # 95/100 clears SPEC.md's illustrative "e.g. >=90%" and even the
    # earlier 95% default, but not the current 99% one -- must not
    # silently detect on a looser bar than what's actually configured.
    sample = [_VALID_RFC5424_LINE] * 95 + [_GARBAGE_LINE] * 5
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
    the ambiguous branch directly by faking two patterns whose parse
    pass always "succeeds" on every sample line, standing in for two
    real formats whose regex banks both happen to clear the bar on the
    same source.
    """
    fake_patterns = [("fake-a", re.compile(".*")), ("fake-b", re.compile(".*"))]
    monkeypatch.setattr(detector, "_KNOWN_PATTERNS", fake_patterns)

    def fake_parse_sample(
        name: str, pattern: re.Pattern[str], sample: list[str]
    ) -> list[EnvelopeSplit | UnknownEnvelopeSplit]:
        return [
            EnvelopeSplit(
                format=name, timestamp="-", marker=None, body=line, raw=line, index=i
            )
            for i, line in enumerate(sample)
        ]

    monkeypatch.setattr(detector, "_parse_sample_against_pattern", fake_parse_sample)
    with pytest.raises(NoMatchingPatternError, match="ambiguous"):
        detect_format(["anything"] * 10)


def test_detect_format_populates_index_on_every_result() -> None:
    sample = [_VALID_RFC5424_LINE] * 99 + [_GARBAGE_LINE] * 1
    result = detect_format(sample)
    assert [r.index for r in result.results] == list(range(100))


def test_detect_format_unknown_splits_contain_failing_lines() -> None:
    sample = [_VALID_RFC5424_LINE] * 99 + [_GARBAGE_LINE]
    result = detect_format(sample)
    assert len(result.envelope_splits) == 99
    assert len(result.unknown_splits) == 1
    unknown = result.unknown_splits[0]
    assert unknown.raw == _GARBAGE_LINE
    assert unknown.attempted_format == "rfc5424-syslog"
    assert unknown.index == 99
    assert "no known envelope pattern matched" not in unknown.reason  # sanity: this
    # message comes from _parse_sample_against_pattern, not split_envelope's wording
    assert unknown.reason  # non-empty, whatever the specific wording is


def test_detect_format_results_preserve_original_order() -> None:
    # Garbage line sandwiched between two valid ones -- results must
    # reflect that exact interleaving, not "all successes then all
    # failures" the way two separately-built lists would collapse it to.
    sample = [_VALID_RFC5424_LINE] * 49 + [_GARBAGE_LINE] + [_VALID_RFC5424_LINE] * 50
    result = detect_format(sample, match_rate_threshold=0.98)
    assert isinstance(result.results[48], EnvelopeSplit)
    assert isinstance(result.results[49], UnknownEnvelopeSplit)
    assert isinstance(result.results[50], EnvelopeSplit)


def test_previous_and_next_result_navigate_across_success_and_failure() -> None:
    sample = [_VALID_RFC5424_LINE] * 49 + [_GARBAGE_LINE] + [_VALID_RFC5424_LINE] * 50
    result = detect_format(sample, match_rate_threshold=0.98)
    unknown = result.unknown_splits[0]
    assert unknown.index == 49

    before = result.previous_result(unknown.index)
    after = result.next_result(unknown.index)
    assert isinstance(before, EnvelopeSplit) and before.index == 48
    assert isinstance(after, EnvelopeSplit) and after.index == 50

    # Navigating from a success works the same way, and finding "the next
    # unknown" from an arbitrary starting point is just walking next_result
    # until isinstance(..., UnknownEnvelopeSplit) -- no separate API needed.
    assert result.previous_result(0) is None
    assert result.next_result(len(result.results) - 1) is None


def test_split_envelope_standalone_has_no_index() -> None:
    result = split_envelope(_VALID_RFC5424_LINE)
    assert result.index is None
