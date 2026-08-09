"""Public Python API — the single place to import PulseForge's stable,
supported surface from. Mirrors parseforge's own api.py convention: one
entry point per pipeline stage (README.md Architecture), plus the types
each one returns or accepts.

Nothing not listed in ``__all__`` is part of the public API and may
change without notice.

SSHConnection/SSHCmdlineBackend (ingestion.backends.ssh_cmdline) are
deliberately not re-exported here, even though they're a real ingestion
backend: that module imports netmiko at the top level, and this file
being importable with only the base install (no ``sampling`` extra) is
exactly the property parseforge itself preserves by not importing
NetmikoSampler from its own api.py either. Import that backend directly
when the sampling extra is actually installed.
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
from .envelope.reassemble import reassemble_lines
from .health.pulse import CategoryHealth, score_health
from .ingestion.backends.file import FileBackend
from .ingestion.core import IngestionBackend, strip_ansi_codes
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
    "reassemble_lines",
    "IngestionBackend",
    "FileBackend",
    "strip_ansi_codes",
    "CategoryResolution",
    "resolve_category",
    "ParsedRecord",
    "parse_body",
    "CategoryHealth",
    "score_health",
    "PulseForgeConfig",
    "run",
]
