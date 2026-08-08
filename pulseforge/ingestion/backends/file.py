"""Reads raw lines from a local log file."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator


class FileBackend:
    def __init__(self, path: Path) -> None:
        self.path = path

    def read_lines(self) -> Iterator[str]:
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                yield line.rstrip("\r\n")
