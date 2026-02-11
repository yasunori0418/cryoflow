"""Plugin base classes for cryoflow."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import polars as pl
from returns.result import Result

FrameData = pl.LazyFrame | pl.DataFrame


class BasePlugin(ABC):
    """Base class for all cryoflow plugins."""

    def __init__(self, options: dict[str, Any], config_dir: Path) -> None:
        """Initialize the plugin.

        Args:
            options: Plugin-specific options dictionary.
            config_dir: Directory containing the config file. Used for resolving
                relative paths.
        """
        self.options = options
        self._config_dir = config_dir

    def resolve_path(self, path: str | Path) -> Path:
        """Resolve a path relative to the config directory.

        Absolute paths are returned as-is (after normalization).
        Relative paths are resolved relative to the config directory.

        Args:
            path: The path to resolve (can be string or Path object).

        Returns:
            The resolved absolute path.

        Example:
            >>> plugin.resolve_path("data/output.parquet")
            PosixPath('/path/to/config/dir/data/output.parquet')
        """
        path = Path(path)
        if not path.is_absolute():
            path = self._config_dir / path
        return path.resolve()

    @abstractmethod
    def name(self) -> str:
        """Return the plugin identifier name."""

    @abstractmethod
    def dry_run(self, schema: dict[str, pl.DataType]) -> Result[dict[str, pl.DataType], Exception]:
        """Validate schema and return expected output schema."""


class TransformPlugin(BasePlugin):
    """Base class for data transformation plugins."""

    @abstractmethod
    def execute(self, df: FrameData) -> Result[FrameData, Exception]:
        """Transform the given data frame."""


class OutputPlugin(BasePlugin):
    """Base class for output plugins."""

    @abstractmethod
    def execute(self, df: FrameData) -> Result[None, Exception]:
        """Output the given data frame."""
