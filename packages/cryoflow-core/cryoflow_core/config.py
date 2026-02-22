"""Configuration models and loader for cryoflow."""

import tomllib
from pathlib import Path
from typing import Any, Optional, NamedTuple

from pydantic import BaseModel, Field
from xdg_base_dirs import xdg_config_home
from returns.result import Result, Failure, safe, Success

from cryoflow_core.result import bind_safe


class PluginConfig(BaseModel):
    """Configuration for a single plugin."""

    name: str
    module: str
    enabled: bool = True
    label: str = 'default'
    options: dict[str, Any] = Field(default_factory=dict)


class CryoflowConfig(BaseModel):
    """Top-level configuration for cryoflow."""

    input_plugins: list[PluginConfig]
    transform_plugins: list[PluginConfig]
    output_plugins: list[PluginConfig]


class ConfigLoadError(Exception):
    """Raised when configuration loading fails."""


class ConfigInfo(NamedTuple):
    """Holds the config file path and its parent directory."""

    file: Path
    directory: Path


_config_bind_safe = bind_safe(ConfigLoadError)


def get_config_path(path: Optional[Path]) -> Path:
    """Returns the `path` passed in the argument or the default `$XDG_CONFIG_HOME/cryoflow/config.toml`.

    - If the argument is None, return `$XDG_CONFIG_HOME/cryoflow/config.toml`
    - If the argument is not None, return the value of the argument
    """
    if path is not None:
        return path
    return xdg_config_home() / 'cryoflow' / 'config.toml'


def _ensure_config_file_exists(config_path: Path) -> Result[Path, ConfigLoadError]:
    """Check that the config file exists and return it wrapped in a Result.

    Args:
        config_path: Path to the config file to check.

    Returns:
        Success containing config_path if the file exists.
        Failure containing ConfigLoadError if the file does not exist.
    """
    if not config_path.exists():
        return Failure(ConfigLoadError(f'Config file not found: {config_path}'))
    return Success(config_path)


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


def load_config(config_path: Path) -> Result[CryoflowConfig, ConfigLoadError]:
    """Load and validate a TOML configuration file.

    Args:
        config_path: Path to the TOML configuration file.

    Returns:
        Success containing a validated CryoflowConfig instance.
        Failure containing ConfigLoadError if the file is not found,
        cannot be read, contains invalid TOML, or fails Pydantic validation.
    """

    def _pipeline(info: ConfigInfo) -> Result[CryoflowConfig, ConfigLoadError]:
        return (
            _read_file(info.file)
            .alt(lambda e: ConfigLoadError(f'Failed to read config file: {e}'))
            .bind(_config_bind_safe(_parse_toml, 'Failed to parse TOML config'))
            .bind(_config_bind_safe(_validate_config, 'Config validation failed'))
        )

    return (
        _ensure_config_file_exists(config_path)
        .map(lambda p: ConfigInfo(file=p, directory=p.parent.resolve()))
        .bind(_pipeline)
    )
