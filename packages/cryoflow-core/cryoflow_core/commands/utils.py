import logging

import typer

from cryoflow_core import __version__


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


def version_callback(value: bool) -> None:
    """Display version and exit.

    Args:
        value: If True, display version and exit.
    """
    if value:
        typer.echo(f'cryoflow version {__version__}')

        # Display plugin collections version if available
        try:
            import cryoflow_plugin_collections

            typer.echo(f'cryoflow-plugin-collections version {cryoflow_plugin_collections.__version__}')
        except (ImportError, AttributeError):
            pass

        raise typer.Exit()
