"""Self-caching index of body-shape -> category, keyed per source (SPEC.md
§3) -- mirrors parseforge.naming.cache's role for cli-name resolution.
"""

from __future__ import annotations

from pathlib import Path


def lookup(cache_path: Path, source: str, body: str) -> str | None:
    raise NotImplementedError


def store(cache_path: Path, source: str, body: str, category: str) -> None:
    raise NotImplementedError
