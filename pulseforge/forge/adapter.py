"""Maps a PulseForge (source, category, body-samples) onto ParseForge's
(vendor/device-family/os, cli-name, cli-samples) pipeline (SPEC.md §4) --
the only place pulseforge imports from parseforge.

A category is passed in wherever ParseForge expects a cli-name; log body
samples are passed in wherever it expects CLI output samples. Everything
downstream of that -- ``run_command_pipeline`` (trial), ``build_integration``,
``promote_auto`` / ``promote_user_reviewed``, ``check_drift`` -- is called
unmodified from :mod:`parseforge.api`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class ForgeResult:
    category: str
    authoritative: bool
    template_path: Path | None


def forge_template(
    root: Path, source: str, category: str, body_samples: Sequence[str]
) -> ForgeResult:
    """Run a category's accumulated body samples through ParseForge's
    trial -> integration -> promotion pipeline (parseforge.api).

    Stub -- see README.md Status.
    """
    raise NotImplementedError
