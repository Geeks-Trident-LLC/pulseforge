"""Persists per-category health history under health/<category>/
(paths.py) so pulse.py can compute rates/ratios against a baseline instead
of only ever seeing the current window.
"""

from __future__ import annotations

from pathlib import Path

from .pulse import CategoryHealth


def append(metrics_root: Path, health: CategoryHealth) -> None:
    raise NotImplementedError


def load_baseline(metrics_root: Path, category: str) -> CategoryHealth | None:
    raise NotImplementedError
