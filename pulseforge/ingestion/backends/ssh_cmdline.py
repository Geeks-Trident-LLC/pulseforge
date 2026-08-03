"""Netmiko-backed backend: runs a log-producing command over SSH (e.g.
``show logging``, ``tail -f /var/log/messages``) and yields its output
line by line. Mirrors parseforge.sampling.backends.netmiko.NetmikoSampler
-- same connection shape, different purpose (a running log source rather
than a single command's output sample).

Requires the optional ``sampling`` extra (``pip install pulseforge[sampling]``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator


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
        raise NotImplementedError
