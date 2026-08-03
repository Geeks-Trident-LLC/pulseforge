"""pulseforge CLI entry point."""

from __future__ import annotations

import click


@click.group()
@click.version_option(package_name="pulseforge")
def main() -> None:
    """PulseForge — categorize, template, and health-score log streams."""


@main.command("run")
@click.option(
    "--source", required=True, help="Identifier for the log source (device/app)."
)
@click.option(
    "--file",
    "file_path",
    type=click.Path(exists=True),
    default=None,
    help="Read raw log lines from a file. Mutually exclusive with --host.",
)
@click.option("--host", default=None, help="SSH into this host and run --command.")
@click.option("--command", default=None, help="Command to run over SSH (with --host).")
@click.option(
    "--root",
    type=click.Path(),
    default="./store",
    show_default=True,
    help="State root for categories/authoritative templates/health history.",
)
def run_cmd(
    source: str,
    file_path: str | None,
    host: str | None,
    command: str | None,
    root: str,
) -> None:
    """Run the full ingestion -> envelope -> naming -> forge -> parse ->
    pulse pipeline against a file or an SSH+cmdline source.

    Stub -- see README.md Status.
    """
    raise NotImplementedError


@main.command("pulse")
@click.option("--category", required=True, help="Category to report health for.")
@click.option(
    "--root", type=click.Path(exists=True), default="./store", show_default=True
)
def pulse_cmd(category: str, root: str) -> None:
    """Print the current health score for a single category.

    Stub -- see README.md Status.
    """
    raise NotImplementedError
