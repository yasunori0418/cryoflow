"""A plugin module loadable via dotpath for testing."""

from typing import Any

import polars as pl
from returns.result import Result, Success

from cryoflow_core.plugin import FrameData, TransformPlugin


class DotpathTransformPlugin(TransformPlugin):
    """Simple transform plugin for dotpath loading tests."""

    def name(self) -> str:
        return 'dotpath_transform'

    def execute(self, df: FrameData) -> Result[FrameData, Exception]:
        return Success(df)

    def dry_run(self, schema: dict[str, pl.DataType]) -> Result[dict[str, pl.DataType], Exception]:
        return Success(schema)
