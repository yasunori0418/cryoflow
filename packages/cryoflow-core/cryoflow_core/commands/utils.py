import logging
from dataclasses import dataclass
from pathlib import Path

import pluggy
import typer
from returns.result import Failure, Result, Success

from cryoflow_core import __version__
from cryoflow_core.config import CryoflowConfig, get_config_path, load_config
from cryoflow_core.loader import get_plugins, load_plugins
from cryoflow_core.plugin import InputPlugin, OutputPlugin, TransformPlugin


@dataclass(frozen=True)
class PipelineSetup:
    """Resolved configuration and plugin instances shared by CLI commands.

    Attributes:
        config_path: Path the configuration was loaded from.
        cfg: The validated cryoflow configuration.
        input_plugins: Registered input plugin instances.
        transform_plugins: Registered transform plugin instances.
        output_plugins: Registered output plugin instances.
    """

    config_path: Path
    cfg: CryoflowConfig
    input_plugins: list[InputPlugin]
    transform_plugins: list[TransformPlugin]
    output_plugins: list[OutputPlugin]


def _as_exception(error: Exception) -> Exception:
    """Widen a specific error type to Exception so Result chains can be combined."""
    return error


def setup_pipeline(config: Path | None) -> Result[PipelineSetup, Exception]:
    """Load configuration and plugins shared by the run and check commands.

    Args:
        config: Explicit config file path, or None to use the default path.

    Returns:
        Success containing the resolved PipelineSetup.
        Failure containing the original error if the config or plugins fail to load,
        or a ValueError if no input or output plugin is configured.
    """
    config_path = get_config_path(config)

    def _build(cfg: CryoflowConfig) -> Result[PipelineSetup, Exception]:
        def _collect(pm: pluggy.PluginManager) -> Result[PipelineSetup, Exception]:
            input_plugins = get_plugins(pm, InputPlugin)
            transform_plugins = get_plugins(pm, TransformPlugin)
            output_plugins = get_plugins(pm, OutputPlugin)

            if len(input_plugins) == 0:
                return Failure(ValueError('No input plugin configured'))

            if len(output_plugins) == 0:
                return Failure(ValueError('No output plugin configured'))

            return Success(
                PipelineSetup(
                    config_path=config_path,
                    cfg=cfg,
                    input_plugins=input_plugins,
                    transform_plugins=transform_plugins,
                    output_plugins=output_plugins,
                )
            )

        return load_plugins(cfg, config_path).alt(_as_exception).bind(_collect)

    return load_config(config_path).alt(_as_exception).bind(_build)


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


def help_callback(ctx: typer.Context, value: bool) -> None:
    """Display help and exit.

    Args:
        ctx: Typer context.
        value: If True, display help and exit.
    """
    if value:
        typer.echo(ctx.get_help())
        raise typer.Exit()
