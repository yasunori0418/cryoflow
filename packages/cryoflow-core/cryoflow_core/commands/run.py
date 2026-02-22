"""cryoflow run"""

from pathlib import Path

from returns.result import Failure
import typer

from cryoflow_core.config import get_config_path, load_config
from cryoflow_core.loader import PluginLoadError, get_plugins, load_plugins
from cryoflow_core.pipeline import run_pipeline
from cryoflow_core.plugin import InputPlugin, OutputPlugin, TransformPlugin


def execute(config: Path | None):
    config_path = get_config_path(config)

    config_result = load_config(config_path)
    if isinstance(config_result, Failure):
        typer.echo(str(config_result.failure()), err=True)
        raise typer.Exit(code=1)
    cfg = config_result.unwrap()

    typer.echo(f'Config loaded: {config_path}')
    typer.echo(f'  input_plugins:     {len(cfg.input_plugins)} plugin(s)')
    for plugin in cfg.input_plugins:
        status = 'enabled' if plugin.enabled else 'disabled'
        typer.echo(f'    - {plugin.name} [{plugin.label}] ({plugin.module}) [{status}]')
    typer.echo(f'  transform_plugins: {len(cfg.transform_plugins)} plugin(s)')
    for plugin in cfg.transform_plugins:
        status = 'enabled' if plugin.enabled else 'disabled'
        typer.echo(f'    - {plugin.name} ({plugin.module}) [{status}]')
    typer.echo(f'  output_plugins:    {len(cfg.output_plugins)} plugin(s)')
    for plugin in cfg.output_plugins:
        status = 'enabled' if plugin.enabled else 'disabled'
        typer.echo(f'    - {plugin.name} ({plugin.module}) [{status}]')

    try:
        pm = load_plugins(cfg, config_path)
    except PluginLoadError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1)

    enabled_count = sum(1 for p in cfg.input_plugins + cfg.transform_plugins + cfg.output_plugins if p.enabled)
    typer.echo(f'Loaded {enabled_count} plugin(s) successfully.')

    # Execute pipeline
    input_plugins = get_plugins(pm, InputPlugin)
    transform_plugins = get_plugins(pm, TransformPlugin)
    output_plugins = get_plugins(pm, OutputPlugin)

    if len(input_plugins) == 0:
        typer.echo('[ERROR] No input plugin configured', err=True)
        raise typer.Exit(code=1)

    if len(output_plugins) == 0:
        typer.echo('[ERROR] No output plugin configured', err=True)
        raise typer.Exit(code=1)

    typer.echo('\nExecuting pipeline...')
    result = run_pipeline(input_plugins, transform_plugins, output_plugins)

    if isinstance(result, Failure):
        error = result.failure()
        typer.echo(f'[ERROR] Pipeline failed: {error}', err=True)
        raise typer.Exit(code=1)

    typer.echo('[SUCCESS] Pipeline completed successfully')
