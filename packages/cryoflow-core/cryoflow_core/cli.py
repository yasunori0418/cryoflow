"""CLI application for cryoflow."""

from pathlib import Path
from typing import Annotated

import typer
from returns.result import Failure

from cryoflow_core.config import ConfigLoadError, get_default_config_path, load_config
from cryoflow_core.loader import PluginLoadError, get_output_plugins, get_transform_plugins, load_plugins
from cryoflow_core.pipeline import run_pipeline

app = typer.Typer(no_args_is_help=True)


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
) -> None:
    """Run the data processing pipeline."""
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
