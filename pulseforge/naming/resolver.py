"""Category resolution entry point: cache lookup first, llm.py on a miss
(SPEC.md §3). Mirrors the cache-then-LLM shape of
parseforge.naming.resolver.cli_name, applied to log bodies instead of CLI
commands.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CategoryResolution:
    category: str
    from_cache: bool


def resolve_category(source: str, marker: str | None, body: str) -> CategoryResolution:
    raise NotImplementedError
