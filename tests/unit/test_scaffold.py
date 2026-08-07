"""Smoke tests confirming the scaffold's modules import and wire together
correctly. Every real behavior test lands alongside its first real
implementation -- see README.md Status.
"""

from __future__ import annotations

import pytest

from pulseforge import api
from pulseforge.cli.main import main as cli_main


def test_api_surface_importable() -> None:
    assert callable(api.split_envelope)
    assert callable(api.resolve_category)
    assert callable(api.parse_body)
    assert callable(api.score_health)
    assert callable(api.run)


def test_cli_group_importable() -> None:
    assert "run" in cli_main.commands
    assert "pulse" in cli_main.commands


def test_stub_stages_raise_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        api.resolve_category("test-source", None, "some body")
