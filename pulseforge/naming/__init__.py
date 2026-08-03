"""Resolves a log body to a category name (SPEC.md §3) — the log-message
equivalent of parseforge.naming's cli-name resolution, but against no
fixed command vocabulary: an LLM proposes the category, self-caching
makes every later body of the same shape a free lookup.

Deliberately not a copy of parseforge/naming/ (including its per-provider
providers/ package) — that module's job is CLI-command tokenization
specifically. This package reuses textfsm-ai's multi-provider call
primitive directly (see llm.py) for a different prompt.
"""
