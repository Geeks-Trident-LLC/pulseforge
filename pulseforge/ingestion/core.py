"""Common backend interface: every ingestion backend yields raw lines,
regardless of source. Mirrors parseforge.sampling.core's role for its own
connector backends.
"""

from __future__ import annotations

import re
from typing import Iterator, Protocol


class IngestionBackend(Protocol):
    def read_lines(self) -> Iterator[str]: ...


# CSI (Control Sequence Introducer) sequences: ESC "[" then zero or more
# parameter/intermediate bytes, then one final letter -- covers SGR color
# codes ("\x1b[31m", "\x1b[0m", ...) and other terminal control sequences
# (cursor movement, erase-in-line, ...) that end up in a log file captured
# via `script`/terminal redirection, or in SSH command output from a
# device/shell that colorizes its own prompts and messages. Deliberately
# scoped to CSI only, not every ANSI escape type (e.g. OSC title-setting
# sequences) -- that's what "color codes" actually means, not a guess at
# every possible terminal escape a source might emit.
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def strip_ansi_codes(line: str) -> str:
    """Remove terminal color/control codes from a line.

    Not cosmetic: RFC 5424's HOSTNAME/APP-NAME/PROC-ID/MSG-ID fields only
    allow printable US-ASCII (patterns.yaml's [\\x21-\\x7E]) -- the ESC
    byte (0x1B) an ANSI sequence starts with falls outside that range, so
    a stray color code left in front of a line breaks split_envelope()'s
    anchored match, not just how the line looks.
    """
    return _ANSI_ESCAPE_RE.sub("", line)
