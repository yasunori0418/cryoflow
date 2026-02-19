"""cryoflow run"""

from pathlib import Path

from returns.result import Failure
import typer

from cryoflow_core.config import get_default_config_path, load_config, ConfigLoadError
from cryoflow_core.loader import PluginLoadError, get_plugins, load_plugins
from cryoflow_core.pipeline import run_pipeline
from cryoflow_core.plugin import OutputPlugin, TransformPlugin


def execute(config: Path | None):
    config_path = config if config is not None else get_default_config_path()

    try:
        cfg = load_config(config_path)
    except ConfigLoadError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)

    typer.echo(f'Config loaded: {config_path}')
    typer.echo(f'  input_path: {cfg.input_path}')
    typer.echo(f'  plugins:    {len(cfg.plugins)} plugin(s)')
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
    transform_plugins = get_plugins(pm, TransformPlugin)
    output_plugins = get_plugins(pm, OutputPlugin)

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
