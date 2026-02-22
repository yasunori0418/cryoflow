"""Parquet input plugin for cryoflow."""

import polars as pl
from returns.result import Failure, Result, Success

from cryoflow_core.plugin import FrameData, InputPlugin


class ParquetScanPlugin(InputPlugin):
    """Load data from a Parquet file using lazy evaluation.

    Options:
        input_path (str | Path): Path to the input Parquet file.
    """

    def name(self) -> str:
        """Return the plugin identifier name."""
        return 'parquet_scan'

    def execute(self) -> Result[FrameData, Exception]:
        """Load data from a Parquet file.

        Returns:
            Result containing LazyFrame on success or Exception on failure.
        """
        try:
            input_path_opt = self.options.get('input_path')
            if input_path_opt is None:
                return Failure(ValueError("Option 'input_path' is required"))
            input_path = self.resolve_path(input_path_opt)
            if not input_path.exists():
                return Failure(FileNotFoundError(f'Input file not found: {input_path}'))
            return Success(pl.scan_parquet(input_path))
        except Exception as e:
            return Failure(e)

    def dry_run(self) -> Result[dict[str, pl.DataType], Exception]:
        """Return the schema of the Parquet file without loading data.

        Returns:
            Result containing schema dict on success or Exception on failure.
        """
        try:
            input_path_opt = self.options.get('input_path')
            if input_path_opt is None:
                return Failure(ValueError("Option 'input_path' is required"))
            input_path = self.resolve_path(input_path_opt)
            if not input_path.exists():
                return Failure(FileNotFoundError(f'Input file not found: {input_path}'))
            return Success(dict(pl.scan_parquet(input_path).collect_schema()))
        except Exception as e:
            return Failure(e)
