"""CSV input plugin for cryoflow."""

from pathlib import Path

import polars as pl
from returns.result import Failure, Result, Success

from cryoflow_core.plugin import FrameData, InputPlugin


class CsvScanPlugin(InputPlugin):
    """Load data from a CSV file using lazy evaluation.

    Options:
        input_path (str): Path to the input CSV file.
    """

    @property
    def name(self) -> str:
        """Return the plugin identifier name."""
        return 'csv_scan'

    def _resolve_input_path(self) -> Result[Path, Exception]:
        """Resolve and validate the input_path option.

        Returns:
            Result containing the resolved path on success or Exception on failure.
        """

        def to_path(value: object) -> Result[Path, Exception]:
            if not isinstance(value, str):
                return Failure(TypeError("Option 'input_path' must be str"))
            input_path = self.resolve_path(value)
            if not input_path.exists():
                return Failure(FileNotFoundError(f'Input file not found: {input_path}'))
            return Success(input_path)

        return self.require_option('input_path').bind(to_path)

    def execute(self) -> Result[FrameData, Exception]:
        """Load data from a CSV file.

        Returns:
            Result containing LazyFrame on success or Exception on failure.
        """
        try:
            return self._resolve_input_path().map(lambda path: pl.scan_csv(path))
        except Exception as e:
            return Failure(e)

    def dry_run(self) -> Result[dict[str, pl.DataType], Exception]:
        """Return the schema of the CSV file without loading data.

        Returns:
            Result containing schema dict on success or Exception on failure.
        """
        try:
            return self._resolve_input_path().map(lambda path: dict(pl.scan_csv(path).collect_schema()))
        except Exception as e:
            return Failure(e)
