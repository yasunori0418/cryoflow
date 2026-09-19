"""Sample output plugin for cryoflow."""

from pathlib import Path

import polars as pl
from returns.result import Failure, Result, Success

from cryoflow_core.plugin import FrameData, OutputPlugin


class ParquetWriterPlugin(OutputPlugin):
    """Write data frame to Parquet file.

    Options:
        output_path (str): Path to the output Parquet file.
    """

    @property
    def name(self) -> str:
        """Return the plugin identifier name."""
        return 'parquet_writer'

    def _resolve_output_path(self) -> Result[Path, Exception]:
        """Resolve and validate the output_path option.

        Returns:
            Result containing the resolved path on success or Exception on failure.
        """

        def to_path(value: object) -> Result[Path, Exception]:
            if not isinstance(value, str):
                return Failure(TypeError("Option 'output_path' must be str"))
            return Success(self.resolve_path(value))

        return self.require_option('output_path').bind(to_path)

    def execute(self, df: FrameData) -> Result[None, Exception]:
        """Write the data frame to a Parquet file.

        Args:
            df: Input LazyFrame or DataFrame.

        Returns:
            Result containing None on success or Exception on failure.
        """

        def write(output_path: Path) -> Result[None, Exception]:
            # Create parent directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write based on frame type
            if isinstance(df, pl.LazyFrame):
                df.sink_parquet(output_path)
            else:  # DataFrame
                df.write_parquet(output_path)

            return Success(None)

        try:
            return self._resolve_output_path().bind(write)
        except Exception as e:
            return Failure(e)

    def dry_run(self, schema: dict[str, pl.DataType]) -> Result[dict[str, pl.DataType], Exception]:
        """Validate that output path is writable.

        Args:
            schema: Input schema (not modified by output plugin).

        Returns:
            Result containing schema unchanged or Exception on failure.
        """

        def check_parent(output_path: Path) -> Result[dict[str, pl.DataType], Exception]:
            # Check if parent directory can be created
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return Failure(ValueError(f'Cannot create parent directory for {output_path}: {e}'))

            return Success(schema)

        try:
            return self._resolve_output_path().bind(check_parent)
        except Exception as e:
            return Failure(e)
