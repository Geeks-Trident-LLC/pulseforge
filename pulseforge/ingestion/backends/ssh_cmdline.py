"""Netmiko-backed backend: runs a log-producing command over SSH once
(e.g. ``show logging``, ``cat /var/log/messages``, or
``SSHCmdlineBackend.tail_file(...)`` for the common "last N lines of a
file" case) and yields its output line by line. Mirrors
parseforge.sampling.backends.netmiko.NetmikoSampler -- same connection
shape (one connection per call, closed on return), same one-shot-command
purpose; the difference is what the caller does with the output
afterward (envelope splitting here, not a TextFSM trial sample).

Requires the optional ``sampling`` extra (``pip install pulseforge[sampling]``)
-- nothing else in ``pulseforge.ingestion`` needs netmiko, only this module,
so it's never imported from ``pulseforge.api`` the way FileBackend is;
import it directly when the sampling extra is actually installed.

Continuous tailing (e.g. an ongoing ``tail -f``) is a different, bigger
design than "run one command, read its output" -- not built here; this
backend is a single snapshot read per call, same as re-running the
command again.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import Iterator, cast

from netmiko import ConnectHandler

from ..core import strip_ansi_codes


@dataclass(frozen=True)
class SSHConnection:
    device_type: str
    host: str
    username: str
    password: str


class SSHCmdlineBackend:
    def __init__(self, connection: SSHConnection, command: str) -> None:
        self.connection = connection
        self.command = command

    @classmethod
    def tail_file(
        cls, connection: SSHConnection, path: str, last_n_lines: int
    ) -> "SSHCmdlineBackend":
        """Convenience constructor for the common "read the last N lines
        of a file over SSH" case: connect, run ``tail -n <N> <path>``,
        close -- the standard POSIX way to express that (there's no real
        ``cat ... last N`` shell syntax). Builds the command so the
        caller doesn't have to hand-construct it (and get the quoting
        wrong) themselves.

        For a target that isn't a POSIX shell -- a network device's own
        CLI, e.g. ``show logging | last 100`` -- construct
        SSHCmdlineBackend directly with whatever command that device
        actually understands; there's no single syntax that works across
        both, so this only covers the POSIX/Linux case.
        """
        if last_n_lines <= 0:
            raise ValueError(f"last_n_lines must be positive, got {last_n_lines}")
        return cls(connection, f"tail -n {last_n_lines} {shlex.quote(path)}")

    def read_lines(self) -> Iterator[str]:
        device = {
            "device_type": self.connection.device_type,
            "host": self.connection.host,
            "username": self.connection.username,
            "password": self.connection.password,
        }
        with ConnectHandler(**device) as conn:
            # send_command()'s stub returns str | list | dict because it can
            # emit structured output when a use_textfsm/use_genie/use_ttp
            # flag is passed -- we never pass one, so this is always a str.
            output = cast(str, conn.send_command(self.command))
        for line in output.splitlines():
            yield strip_ansi_codes(line)
