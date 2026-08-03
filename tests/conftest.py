"""Shared pytest configuration.

--real gates integration tests that hit real, costly external resources
(LLM API calls, live SSH connections) -- skipped by default, mirroring
parseforge/tests/conftest.py's own --real gate.
"""

from __future__ import annotations

import os

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--real",
        action="store_true",
        default=False,
        help="Run integration tests that hit real external resources "
        "(costs money and/or needs credentials or network access).",
    )


@pytest.fixture(scope="session")
def require_real_tests(request: pytest.FixtureRequest) -> None:
    if not request.config.getoption("--real"):
        pytest.skip("real-resource test skipped — pass --real to run it")


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"{name} not set — required for real-resource tests")
    return value


@pytest.fixture(scope="session")
def anthropic_key(require_real_tests: None) -> str:
    return _require_env("ANTHROPIC_API_KEY")
