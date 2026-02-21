"""Configuration models and loader for cryoflow."""

import tomllib
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field
from xdg_base_dirs import xdg_config_home
from returns.result import Result, Failure, safe


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


@safe
def _read_file(path: Path) -> bytes:
    """Read file bytes from path.

    Raises:
        OSError: If the file cannot be read.
    """
    return path.read_bytes()


@safe
def _parse_toml(raw: bytes) -> dict:
    """Parse TOML bytes to a dictionary.

    Raises:
        tomllib.TOMLDecodeError: If the TOML syntax is invalid.
    """
    return tomllib.loads(raw.decode())


@safe
def _validate_config(data: dict) -> CryoflowConfig:
    """Validate raw config dict against CryoflowConfig schema.

    Raises:
        Exception: If Pydantic validation fails.
    """
    return CryoflowConfig(**data)


def _apply_path_resolution(cfg: CryoflowConfig, config_dir: Path) -> CryoflowConfig:
    """Apply input_path resolution relative to config directory."""
    cfg.input_path = _resolve_path_relative_to_config(cfg.input_path, config_dir)
    return cfg


def load_config(config_path: Path) -> Result[CryoflowConfig, ConfigLoadError]:
    """Load and validate a TOML configuration file.

    Args:
        config_path: Path to the TOML configuration file.

    Returns:
        Success containing a validated CryoflowConfig instance with
        input_path resolved relative to the config file directory.
        Failure containing ConfigLoadError if the file is not found,
        cannot be read, contains invalid TOML, or fails Pydantic validation.

    Note:
        Relative paths in input_path are resolved relative to the directory
        containing the config file, not the current working directory.
    """
    if not config_path.exists():
        return Failure(ConfigLoadError(f'Config file not found: {config_path}'))

    config_dir = config_path.parent.resolve()

    return (
        _read_file(config_path)
        .alt(lambda e: ConfigLoadError(f'Failed to read config file: {e}'))
        .bind(lambda raw: _parse_toml(raw).alt(lambda e: ConfigLoadError(f'Failed to parse TOML config: {e}')))
        .bind(lambda data: _validate_config(data).alt(lambda e: ConfigLoadError(f'Config validation failed: {e}')))
        .map(lambda cfg: _apply_path_resolution(cfg, config_dir))
    )
