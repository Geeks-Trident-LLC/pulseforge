"""Tests for ingestion/backends/file.py."""

from __future__ import annotations

from pathlib import Path

from pulseforge.ingestion.backends.file import FileBackend


def test_read_lines_yields_stripped_lines(tmp_path: Path) -> None:
    path = tmp_path / "log.txt"
    path.write_text("first line\nsecond line\nthird line\n", encoding="utf-8")

    lines = list(FileBackend(path).read_lines())

    assert lines == ["first line", "second line", "third line"]


def test_read_lines_handles_no_trailing_newline(tmp_path: Path) -> None:
    path = tmp_path / "log.txt"
    path.write_text("first line\nsecond line", encoding="utf-8")

    lines = list(FileBackend(path).read_lines())

    assert lines == ["first line", "second line"]


def test_read_lines_handles_crlf_line_endings(tmp_path: Path) -> None:
    path = tmp_path / "log.txt"
    # Write raw bytes so the CRLF isn't translated away before FileBackend
    # ever sees it -- exercises its own rstrip, not just Python's default
    # universal-newlines translation on open().
    path.write_bytes(b"first line\r\nsecond line\r\n")

    lines = list(FileBackend(path).read_lines())

    assert lines == ["first line", "second line"]


def test_read_lines_empty_file_yields_nothing(tmp_path: Path) -> None:
    path = tmp_path / "empty.txt"
    path.write_text("", encoding="utf-8")

    assert list(FileBackend(path).read_lines()) == []


def test_read_lines_preserves_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "log.txt"
    path.write_text("first line\n\nthird line\n", encoding="utf-8")

    lines = list(FileBackend(path).read_lines())

    assert lines == ["first line", "", "third line"]
