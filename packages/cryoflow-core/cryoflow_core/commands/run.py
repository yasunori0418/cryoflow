"""cryoflow run"""

from pathlib import Path

import typer
from returns.result import Failure

from cryoflow_core.commands.utils import setup_pipeline
from cryoflow_core.pipeline import run_pipeline


def execute(config: Path | None):
    setup_result = setup_pipeline(config)
    if isinstance(setup_result, Failure):
        error = setup_result.failure()
        message = f'[ERROR] {error}' if isinstance(error, ValueError) else str(error)
        typer.echo(message, err=True)
        raise typer.Exit(code=1)
    setup = setup_result.unwrap()

    cfg = setup.cfg
    typer.echo(f'Config loaded: {setup.config_path}')
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

    enabled_count = sum(1 for p in cfg.input_plugins + cfg.transform_plugins + cfg.output_plugins if p.enabled)
    typer.echo(f'Loaded {enabled_count} plugin(s) successfully.')

    typer.echo('\nExecuting pipeline...')
    result = run_pipeline(setup.input_plugins, setup.transform_plugins, setup.output_plugins)

    if isinstance(result, Failure):
        error = result.failure()
        typer.echo(f'[ERROR] Pipeline failed: {error}', err=True)
        raise typer.Exit(code=1)

    typer.echo('[SUCCESS] Pipeline completed successfully')
