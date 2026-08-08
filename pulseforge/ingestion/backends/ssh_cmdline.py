"""Netmiko-backed backend: runs a log-producing command over SSH once
(e.g. ``show logging``, ``cat /var/log/messages``) and yields its output
line by line. Mirrors parseforge.sampling.backends.netmiko.NetmikoSampler
-- same connection shape (one connection per call, closed on return), same
one-shot-command purpose; the difference is what the caller does with the
output afterward (envelope splitting here, not a TextFSM trial sample).

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
