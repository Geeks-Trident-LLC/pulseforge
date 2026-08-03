"""Common backend interface: every ingestion backend yields raw lines,
regardless of source. Mirrors parseforge.sampling.core's role for its own
connector backends.
"""

from __future__ import annotations

from typing import Iterator, Protocol


class IngestionBackend(Protocol):
    def read_lines(self) -> Iterator[str]: ...
