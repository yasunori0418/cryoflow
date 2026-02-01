"""CLI application for cryoflow."""

import logging
from pathlib import Path
from typing import Annotated

import typer
from returns.result import Failure

from cryoflow_core.config import ConfigLoadError, get_default_config_path, load_config
from cryoflow_core.loader import PluginLoadError, get_output_plugins, get_transform_plugins, load_plugins
from cryoflow_core.pipeline import run_pipeline, run_dry_run_pipeline  # noqa: F401

app = typer.Typer(no_args_is_help=True)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for CLI.

    Args:
        verbose: If True, set log level to DEBUG; otherwise INFO.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format='%(levelname)s: %(message)s',
        level=level,
    )


@app.callback()
def main() -> None:
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
            '-v',
            '--verbose',
            help='Enable verbose output.',
        ),
    ] = False,
) -> None:
    """Run the data processing pipeline."""
    setup_logging(verbose)
    config_path = config if config is not None else get_default_config_path()

    try:
        cfg = load_config(config_path)
    except ConfigLoadError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)

    typer.echo(f'Config loaded: {config_path}')
    typer.echo(f'  input_path:    {cfg.input_path}')
    typer.echo(f'  output_target: {cfg.output_target}')
    typer.echo(f'  plugins:       {len(cfg.plugins)} plugin(s)')
    for plugin in cfg.plugins:
        status = 'enabled' if plugin.enabled else 'disabled'
        typer.echo(f'    - {plugin.name} ({plugin.module}) [{status}]')

    try:
        pm = load_plugins(cfg, config_path)
    except PluginLoadError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)

    enabled_count = sum(1 for p in cfg.plugins if p.enabled)
    typer.echo(f'Loaded {enabled_count} plugin(s) successfully.')

    # Execute pipeline
    transform_plugins = get_transform_plugins(pm)
    output_plugins = get_output_plugins(pm)

    if len(output_plugins) == 0:
        typer.echo('[ERROR] No output plugin configured', err=True)
        raise typer.Exit(code=1)
    if len(output_plugins) > 1:
        typer.echo('[ERROR] Multiple output plugins not supported yet', err=True)
        raise typer.Exit(code=1)

    typer.echo('\nExecuting pipeline...')
    result = run_pipeline(cfg.input_path, transform_plugins, output_plugins[0])

    if isinstance(result, Failure):
        error = result.failure()
        typer.echo(f'[ERROR] Pipeline failed: {error}', err=True)
        raise typer.Exit(code=1)

    typer.echo('[SUCCESS] Pipeline completed successfully')


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
            '-v',
            '--verbose',
            help='Enable verbose output.',
        ),
    ] = False,
) -> None:
    """Validate pipeline configuration and schema without processing data."""
    setup_logging(verbose)
    config_path = config if config is not None else get_default_config_path()

    # Config loading
    try:
        cfg = load_config(config_path)
    except ConfigLoadError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)

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
    transform_plugins = get_transform_plugins(pm)
    output_plugins = get_output_plugins(pm)

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
