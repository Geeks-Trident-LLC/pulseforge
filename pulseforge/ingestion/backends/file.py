"""Reads raw lines from a local log file."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator


class FileBackend:
    def __init__(self, path: Path) -> None:
        self.path = path

    def read_lines(self) -> Iterator[str]:
        raise NotImplementedError
