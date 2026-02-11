"""Configuration models and loader for cryoflow."""

import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from xdg_base_dirs import xdg_config_home


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


def get_default_config_path() -> Path:
    """Return the default config file path following XDG Base Directory spec."""
    return xdg_config_home() / 'cryoflow' / 'config.toml'


def load_config(config_path: Path) -> CryoflowConfig:
    """Load and validate a TOML configuration file.

    Args:
        config_path: Path to the TOML configuration file.

    Returns:
        Validated CryoflowConfig instance.

    Raises:
        ConfigLoadError: If the file is not found, TOML parsing fails,
            or Pydantic validation fails.
    """
    if not config_path.exists():
        raise ConfigLoadError(f'Config file not found: {config_path}')

    try:
        raw = config_path.read_bytes()
    except OSError as e:
        raise ConfigLoadError(f'Failed to read config file: {e}') from e

    try:
        data = tomllib.loads(raw.decode())
    except tomllib.TOMLDecodeError as e:
        raise ConfigLoadError(f'Failed to parse TOML config: {e}') from e

    try:
        return CryoflowConfig(**data)
    except Exception as e:
        raise ConfigLoadError(f'Config validation failed: {e}') from e
