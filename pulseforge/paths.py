"""On-disk layout for PulseForge's own state.

Trial/integration/authoritative directories for a category are owned and
written by ``parseforge`` itself (pulseforge only ever calls
:mod:`parseforge.api` and passes a category name where ParseForge expects
a cli-name — see forge/adapter.py). The one tier ParseForge has no
equivalent of, and that this module does own, is ``health/`` (SPEC.md §5).

Shared path shape: ``<source>/<category>/`` (SPEC.md §4) — e.g.
``cisco-ios/link-updown/``.
"""

from __future__ import annotations

from pathlib import Path


def health_dir(root: Path, source: str, category: str) -> Path:
    raise NotImplementedError


def category_cache_path(root: Path) -> Path:
    raise NotImplementedError


def envelope_cache_path(root: Path) -> Path:
    raise NotImplementedError
