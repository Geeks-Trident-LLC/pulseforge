"""Reads raw lines from a local log file."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from ..core import strip_ansi_codes


class FileBackend:
    def __init__(self, path: Path) -> None:
        self.path = path

    def read_lines(self) -> Iterator[str]:
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                yield strip_ansi_codes(line.rstrip("\r\n"))
