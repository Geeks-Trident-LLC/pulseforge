"""LLM-driven category naming for a log body (SPEC.md §3).

Only called on a cache miss (see resolver.py / cache.py). Uses
``textfsm-ai``'s multi-provider call primitive directly -- the same
underlying package parseforge itself is built on -- rather than going
through parseforge.naming, whose prompt and provider wiring is specific to
CLI-command tokenization, not log-body categorization.
"""

from __future__ import annotations

from dataclasses import dataclass

from .prompts import load_prompt_template

PROMPT_TEMPLATE = load_prompt_template("log_body_category")


@dataclass(frozen=True)
class LLMCategoryResponse:
    category: str
    raw: object


def build_prompt(marker: str | None, body: str) -> str:
    raise NotImplementedError


def resolve_category_via_llm(marker: str | None, body: str) -> LLMCategoryResponse:
    raise NotImplementedError
