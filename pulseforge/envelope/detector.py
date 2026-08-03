"""Envelope/body split (SPEC.md §2).

Detection order: known-format regex bank (patterns.yaml) first, since it's
free; an LLM-proposed split regex only on a shape none of those match,
cached afterward the same way naming/cache.py caches category resolutions
so a given source only ever pays that cost once per distinct envelope
shape.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EnvelopeSplit:
    timestamp: str
    marker: str | None
    body: str
    raw: str


def split_envelope(line: str) -> EnvelopeSplit:
    raise NotImplementedError


def load_known_patterns() -> list[str]:
    """Load the regex bank from patterns.yaml."""
    raise NotImplementedError
