"""Configuration models and loader for cryoflow."""

import tomllib
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field
from xdg_base_dirs import xdg_config_home
from returns.result import Result, Success, Failure


class PluginConfig(BaseModel):
    """Configuration for a single plugin."""

    name: str
    module: str
    enabled: bool = True
    options: dict[str, Any] = Field(default_factory=dict)


class CryoflowConfig(BaseModel):
    """Top-level configuration for cryoflow."""

    input_path: Path
    plugins: list[PluginConfig]


class ConfigLoadError(Exception):
    """Raised when configuration loading fails."""


def get_config_path(path: Optional[Path]) -> Path:
    """Returns the `path` passed in the argument or the default `$XDG_CONFIG_HOME/cryoflow/config.toml`.

    - If the argument is None, return `$XDG_CONFIG_HOME/cryoflow/config.toml`
    - If the argument is not None, return the value of the argument
    """
    if path is not None:
        return path
    return xdg_config_home() / 'cryoflow' / 'config.toml'


def _resolve_path_relative_to_config(path: Path, config_dir: Path) -> Path:
    """Resolve a path relative to the config file directory.

    Absolute paths are normalized with resolve().
    Relative paths are resolved relative to config_dir.

    Args:
        path: The path to resolve.
        config_dir: The directory containing the config file.

    Returns:
        The resolved absolute path.

    Note:
        This function does not check if the file exists.
        File existence should be validated at the appropriate stage
        (e.g., in pipeline.py when opening the file).
    """
    if not path.is_absolute():
        path = config_dir / path
    return path.resolve()


def load_config(config_path: Path) -> Result[CryoflowConfig, ConfigLoadError]:
    """Load and validate a TOML configuration file.

    Args:
        config_path: Path to the TOML configuration file.

    Returns:
        Validated CryoflowConfig instance with input_path resolved relative
        to the config file directory.

    Raises:
        ConfigLoadError: If the file is not found, TOML parsing fails,
            or Pydantic validation fails.

    Note:
        Relative paths in input_path are resolved relative to the directory
        containing the config file, not the current working directory.
    """
    if not config_path.exists():
        return Failure(ConfigLoadError(f'Config file not found: {config_path}'))

    try:
        raw = config_path.read_bytes()
    except OSError as e:
        return Failure(ConfigLoadError(f'Failed to read config file: {e}'))

    try:
        data = tomllib.loads(raw.decode())
    except tomllib.TOMLDecodeError as e:
        return Failure(ConfigLoadError(f'Failed to parse TOML config: {e}'))

    try:
        cfg = CryoflowConfig(**data)
    except Exception as e:
        return Failure(ConfigLoadError(f'Config validation failed: {e}'))

    # Resolve input_path relative to config directory
    config_dir = config_path.parent.resolve()
    cfg.input_path = _resolve_path_relative_to_config(cfg.input_path, config_dir)

    return Success(cfg)
