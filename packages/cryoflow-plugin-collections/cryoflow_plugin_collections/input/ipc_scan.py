"""IPC (Arrow) input plugin for cryoflow."""

import polars as pl
from returns.result import Failure, Result, Success

from cryoflow_core.plugin import FrameData, InputPlugin


class IpcScanPlugin(InputPlugin):
    """Load data from an IPC (Arrow) file using lazy evaluation.

    Options:
        input_path (str | Path): Path to the input IPC file.
    """

    def name(self) -> str:
        """Return the plugin identifier name."""
        return 'ipc_scan'

    def execute(self) -> Result[FrameData, Exception]:
        """Load data from an IPC file.

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
            return Success(pl.scan_ipc(input_path))
        except Exception as e:
            return Failure(e)

    def dry_run(self) -> Result[dict[str, pl.DataType], Exception]:
        """Return the schema of the IPC file without loading data.

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
            return Success(dict(pl.scan_ipc(input_path).collect_schema()))
        except Exception as e:
            return Failure(e)
