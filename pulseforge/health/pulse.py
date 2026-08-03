"""Computes a category's health score from recent parsed records
(SPEC.md §5): match rate, frequency vs. baseline, field-value
distribution. A sustained match-rate drop is expected to feed back into
``parseforge.drift.check_drift`` as a new trial, the same way ParseForge
already closes that loop for CLI templates -- this module only owns the
detection, not the retraining.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from ..parsing.engine import ParsedRecord


@dataclass(frozen=True)
class CategoryHealth:
    category: str
    match_rate: float
    frequency_ratio: float
    inconsistent: bool


def score_health(
    metrics_root: Path, category: str, records: Sequence[ParsedRecord]
) -> CategoryHealth:
    raise NotImplementedError
