"""Public Python API — the single place to import PulseForge's stable,
supported surface from. Mirrors parseforge's own api.py convention: one
entry point per pipeline stage (README.md Architecture), plus the types
each one returns or accepts.

Nothing not listed in ``__all__`` is part of the public API and may
change without notice.
"""

from __future__ import annotations

from .envelope.detector import (
    EnvelopeSplit,
    FormatDetectionResult,
    NoMatchingPatternError,
    UnknownEnvelopeSplit,
    detect_format,
    split_envelope,
)
from .health.pulse import CategoryHealth, score_health
from .naming.resolver import CategoryResolution, resolve_category
from .parsing.engine import ParsedRecord, parse_body
from .pipeline import PulseForgeConfig, run

__all__ = [
    "EnvelopeSplit",
    "FormatDetectionResult",
    "UnknownEnvelopeSplit",
    "NoMatchingPatternError",
    "split_envelope",
    "detect_format",
    "CategoryResolution",
    "resolve_category",
    "ParsedRecord",
    "parse_body",
    "CategoryHealth",
    "score_health",
    "PulseForgeConfig",
    "run",
]
