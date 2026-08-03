"""YAML config-file loading for the `run` CLI command -- CLI input parsing,
not domain logic, mirroring parseforge.cli.config's role there.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunConfig:
    source: str
    root: Path


def load_run_config(path: Path) -> RunConfig:
    raise NotImplementedError
