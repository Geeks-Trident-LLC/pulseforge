"""Orchestrates the full flow (README.md Architecture):

    ingestion -> envelope split -> category naming -> template forge
              -> parse -> pulse/health scoring -> sink

Each stage is implemented in its own package (envelope/, naming/, forge/,
parsing/, health/) and imported here rather than reimplemented; this
module's only job is sequencing and passing each stage's output to the
next, mirroring parseforge.pipeline's own role for its stages.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class PulseForgeConfig:
    """Run configuration: state root, source identifier, provider choice,
    and whatever thresholds §5's health scoring needs. Fleshed out once
    the stub stages below have real parameters to configure.
    """

    root: Path
    source: str


def run(config: PulseForgeConfig, lines: Iterable[str]) -> None:
    """Run every raw line through the full pipeline in sequence.

    Stub: each stage this delegates to currently raises
    NotImplementedError. See README.md Status.
    """
    raise NotImplementedError
