"""cryoflow check"""

from pathlib import Path

import typer
from returns.result import Failure

from cryoflow_core.commands.utils import setup_pipeline
from cryoflow_core.pipeline import run_dry_run_pipeline


def execute(config: Path | None):
    setup_result = setup_pipeline(config)
    if isinstance(setup_result, Failure):
        error = setup_result.failure()
        message = f'[ERROR] {error}' if isinstance(error, ValueError) else str(error)
        typer.echo(message, err=True)
        raise typer.Exit(code=1)
    setup = setup_result.unwrap()

    typer.echo(f'[CHECK] Config loaded: {setup.config_path}')

    cfg = setup.cfg
    enabled_count = sum(1 for p in cfg.input_plugins + cfg.transform_plugins + cfg.output_plugins if p.enabled)
    typer.echo(f'[CHECK] Loaded {enabled_count} plugin(s) successfully.')

    typer.echo('\n[CHECK] Running dry-run validation...')

    result = run_dry_run_pipeline(setup.input_plugins, setup.transform_plugins, setup.output_plugins)

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
