"""Applies an authoritative TextFSM template to a log body and returns
structured fields. Delegates the actual TextFSM run to
``parseforge.validation.parse(template_text, input_text)`` -- the same
function ParseForge uses to self-validate a freshly generated template --
rather than reimplementing TextFSM invocation here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ParsedRecord:
    category: str
    fields: dict[str, Any]
    matched: bool


def parse_body(template_text: str, category: str, body: str) -> ParsedRecord:
    raise NotImplementedError
