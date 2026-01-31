"""Plugin base classes for cryoflow."""

from abc import ABC, abstractmethod
from typing import Any

import polars as pl
from returns.result import Result

FrameData = pl.LazyFrame | pl.DataFrame


class BasePlugin(ABC):
    """Base class for all cryoflow plugins."""

    def __init__(self, options: dict[str, Any]) -> None:
        self.options = options

    @abstractmethod
    def name(self) -> str:
        """Return the plugin identifier name."""

    @abstractmethod
    def dry_run(
        self, schema: dict[str, pl.DataType]
    ) -> Result[dict[str, pl.DataType], Exception]:
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
