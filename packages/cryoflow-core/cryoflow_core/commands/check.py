"""cryoflow check"""

from pathlib import Path

import typer
from returns.result import Failure

from cryoflow_core.config import get_config_path, load_config
from cryoflow_core.loader import PluginLoadError, get_plugins, load_plugins
from cryoflow_core.pipeline import run_dry_run_pipeline
from cryoflow_core.plugin import OutputPlugin, TransformPlugin


def execute(config: Path | None):
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

    enabled_count = sum(1 for p in cfg.transform_plugins + cfg.output_plugins if p.enabled)
    typer.echo(f'[CHECK] Loaded {enabled_count} plugin(s) successfully.')

    # Execute dry-run validation
    transform_plugins = get_plugins(pm, TransformPlugin)
    output_plugins = get_plugins(pm, OutputPlugin)

    if len(output_plugins) == 0:
        typer.echo('[ERROR] No output plugin configured', err=True)
        raise typer.Exit(code=1)

    typer.echo('\n[CHECK] Running dry-run validation...')

    result = run_dry_run_pipeline(cfg.input_path, transform_plugins, output_plugins)

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
