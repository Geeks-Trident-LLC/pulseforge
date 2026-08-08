"""Tests for ingestion/backends/ssh_cmdline.py.

ConnectHandler is always mocked here -- these never touch a real network
or device, only verify SSHCmdlineBackend calls it correctly and splits
whatever it returns.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import pulseforge.ingestion.backends.ssh_cmdline as ssh_cmdline
from pulseforge.ingestion.backends.ssh_cmdline import SSHCmdlineBackend, SSHConnection


def _mock_connect_handler(output: str) -> MagicMock:
    mock_conn = MagicMock()
    mock_conn.send_command.return_value = output
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    return MagicMock(return_value=mock_conn)


def test_read_lines_runs_command_and_splits_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_connect_handler = _mock_connect_handler("line one\nline two\nline three")
    monkeypatch.setattr(ssh_cmdline, "ConnectHandler", mock_connect_handler)

    connection = SSHConnection(
        device_type="cisco_ios", host="10.0.0.1", username="admin", password="secret"
    )
    lines = list(SSHCmdlineBackend(connection, "show logging").read_lines())

    assert lines == ["line one", "line two", "line three"]
    mock_connect_handler.assert_called_once_with(
        device_type="cisco_ios",
        host="10.0.0.1",
        username="admin",
        password="secret",
    )
    conn = mock_connect_handler.return_value
    conn.send_command.assert_called_once_with("show logging")


def test_read_lines_handles_empty_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ssh_cmdline, "ConnectHandler", _mock_connect_handler(""))
    connection = SSHConnection(
        device_type="cisco_ios", host="10.0.0.1", username="admin", password="secret"
    )

    assert list(SSHCmdlineBackend(connection, "show logging").read_lines()) == []


def test_read_lines_handles_trailing_newline_without_empty_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ssh_cmdline, "ConnectHandler", _mock_connect_handler("line one\nline two\n")
    )
    connection = SSHConnection(
        device_type="cisco_ios", host="10.0.0.1", username="admin", password="secret"
    )

    lines = list(SSHCmdlineBackend(connection, "show logging").read_lines())

    assert lines == ["line one", "line two"]
