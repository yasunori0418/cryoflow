"""CLI application for cryoflow."""

from pathlib import Path
from typing import Annotated

import typer

from cryoflow_core.commands import utils, run as run_executor, check as check_executor

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main(
    _version: Annotated[
        bool,
        typer.Option(
            '-v',
            '--version',
            callback=utils.version_callback,
            is_eager=True,
            help='Show version and exit.',
        ),
    ] = False,
    _help: Annotated[
        bool,
        typer.Option(
            '-h',
            '--help',
            callback=utils.help_callback,
            is_eager=True,
            help='Show this message and exit.',
        ),
    ] = False,
) -> None:
    """cryoflow: Plugin-driven columnar data processing CLI."""


@app.command()
def run(
    config: Annotated[
        Path | None,
        typer.Option(
            '-c',
            '--config',
            help='Path to config file.',
            exists=True,
            dir_okay=False,
            resolve_path=True,
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option(
            '-V',
            '--verbose',
            help='Enable verbose output.',
        ),
    ] = False,
    _help: Annotated[
        bool,
        typer.Option(
            '-h',
            '--help',
            callback=utils.help_callback,
            is_eager=True,
            help='Show this message and exit.',
        ),
    ] = False,
) -> None:
    """Run the data processing pipeline."""
    utils.setup_logging(verbose)
    run_executor.execute(config)


@app.command()
def check(
    config: Annotated[
        Path | None,
        typer.Option(
            '-c',
            '--config',
            help='Path to config file.',
            exists=True,
            dir_okay=False,
            resolve_path=True,
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option(
            '-V',
            '--verbose',
            help='Enable verbose output.',
        ),
    ] = False,
    _help: Annotated[
        bool,
        typer.Option(
            '-h',
            '--help',
            callback=utils.help_callback,
            is_eager=True,
            help='Show this message and exit.',
        ),
    ] = False,
) -> None:
    """Validate pipeline configuration and schema without processing data."""
    utils.setup_logging(verbose)
    check_executor.execute(config)
