"""CLI application for cryoflow."""

from pathlib import Path
from typing import Annotated

import typer
from returns.result import Failure

from cryoflow_core.commands import utils, run as run_executor
from cryoflow_core.config import get_config_path, load_config
from cryoflow_core.loader import PluginLoadError, get_plugins, load_plugins
from cryoflow_core.pipeline import run_dry_run_pipeline  # noqa: F401
from cryoflow_core.plugin import OutputPlugin, TransformPlugin

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
    config_path = get_config_path(config)

    # Config loading
    config_result = load_config(config_path)
    if isinstance(config_result, Failure):
        typer.echo(str(config_result.failure()), err=True)
        raise typer.Exit(code=1)
    cfg = config_result.unwrap()

    typer.echo(f'[CHECK] Config loaded: {config_path}')

    # Plugin loading
    try:
        pm = load_plugins(cfg, config_path)
    except PluginLoadError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)

    enabled_count = sum(1 for p in cfg.plugins if p.enabled)
    typer.echo(f'[CHECK] Loaded {enabled_count} plugin(s) successfully.')

    # Execute dry-run validation
    transform_plugins = get_plugins(pm, TransformPlugin)
    output_plugins = get_plugins(pm, OutputPlugin)

    if len(output_plugins) == 0:
        typer.echo('[ERROR] No output plugin configured', err=True)
        raise typer.Exit(code=1)
    if len(output_plugins) > 1:
        typer.echo('[ERROR] Multiple output plugins not supported yet', err=True)
        raise typer.Exit(code=1)

    typer.echo('\n[CHECK] Running dry-run validation...')

    result = run_dry_run_pipeline(cfg.input_path, transform_plugins, output_plugins[0])

    if isinstance(result, Failure):
        error = result.failure()
        typer.echo(f'[ERROR] Validation failed: {error}', err=True)
        raise typer.Exit(code=1)

    # Display final schema
    final_schema = result.unwrap()
    typer.echo('\n[SUCCESS] Validation completed successfully')
    typer.echo('\nOutput schema:')
    for col_name, dtype in final_schema.items():
        typer.echo(f'  {col_name}: {dtype}')
