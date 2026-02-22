"""Sample output plugin for cryoflow."""

from pathlib import Path

import polars as pl
from returns.result import Failure, Result, Success

from cryoflow_core.plugin import FrameData, OutputPlugin


class ParquetWriterPlugin(OutputPlugin):
    """Write data frame to Parquet file.

    Options:
        output_path (str | Path): Path to the output Parquet file.
    """

    def name(self) -> str:
        """Return the plugin identifier name."""
        return 'parquet_writer'

    def execute(self, df: FrameData) -> Result[None, Exception]:
        """Write the data frame to a Parquet file.

        Args:
            df: Input LazyFrame or DataFrame.

        Returns:
            Result containing None on success or Exception on failure.
        """
        try:
            output_path_opt = self.options.get('output_path')
            if output_path_opt is None:
                return Failure(ValueError("Option 'output_path' is required"))

            output_path = self.resolve_path(output_path_opt)

            # Create parent directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write based on frame type
            if isinstance(df, pl.LazyFrame):
                df.sink_parquet(output_path)
            else:  # DataFrame
                df.write_parquet(output_path)

            return Success(None)
        except Exception as e:
            return Failure(e)

    def dry_run(self, schema: dict[str, pl.DataType]) -> Result[dict[str, pl.DataType], Exception]:
        """Validate that output path is writable.

        Args:
            schema: Input schema (not modified by output plugin).

        Returns:
            Result containing schema unchanged or Exception on failure.
        """
        try:
            output_path_opt = self.options.get('output_path')
            if output_path_opt is None:
                return Failure(ValueError("Option 'output_path' is required"))

            output_path = self.resolve_path(output_path_opt)

            # Check if parent directory can be created
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return Failure(ValueError(f'Cannot create parent directory for {output_path}: {e}'))

            return Success(schema)
        except Exception as e:
            return Failure(e)
