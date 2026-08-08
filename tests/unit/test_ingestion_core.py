"""Tests for ingestion/core.py's strip_ansi_codes()."""

from __future__ import annotations

from pulseforge.envelope.detector import split_envelope
from pulseforge.ingestion.core import strip_ansi_codes


def test_strips_sgr_color_code() -> None:
    assert strip_ansi_codes("\x1b[31mERROR\x1b[0m: something bad happened") == (
        "ERROR: something bad happened"
    )


def test_strips_cursor_and_erase_codes() -> None:
    assert strip_ansi_codes("\x1b[2K\x1b[1;32mOK\x1b[0m") == "OK"


def test_strips_multiple_codes_in_one_line() -> None:
    assert strip_ansi_codes("\x1b[1;32mOK\x1b[0m \x1b[33mWARN\x1b[0m") == "OK WARN"


def test_line_without_codes_is_unchanged() -> None:
    line = "plain log line, no escape codes at all"
    assert strip_ansi_codes(line) == line


def test_empty_string() -> None:
    assert strip_ansi_codes("") == ""


def test_leading_color_code_no_longer_breaks_rfc5424_matching() -> None:
    """The actual motivating bug, not just a cosmetic concern: RFC 5424's
    HOSTNAME/APP-NAME/etc. fields only allow printable US-ASCII
    ([\\x21-\\x7E]), which excludes the ESC byte (0x1B) a color code
    starts with -- so a line with one left in front used to fail
    split_envelope()'s anchored match entirely, not just look noisy.
    """
    colored = (
        "\x1b[36m<34>1 2003-10-11T22:14:15.003Z mymachine.example.com su "
        "- ID47 - 'su root' failed for lonvick on /dev/pts/8\x1b[0m"
    )
    cleaned = strip_ansi_codes(colored)
    result = split_envelope(cleaned)
    assert result.format == "rfc5424-syslog"
    assert result.body == "'su root' failed for lonvick on /dev/pts/8"
