"""Tests for execute_output_dry_run function."""

from pathlib import Path

import polars as pl
from returns.result import Failure, Success

from cryoflow_core.pipeline import execute_output_dry_run
from cryoflow_core.plugin import FrameData, OutputPlugin


class TestExecuteOutputDryRun:
    """Tests for output plugin dry-run execution."""

    def test_output_dry_run_success(self, tmp_path: Path) -> None:
        """Test output dry-run with successful validation."""
        from returns.result import Success as SuccessResult

        class DummyOutputPlugin(OutputPlugin):
            def name(self) -> str:
                return 'dummy_output'

            def execute(self, df: FrameData) -> SuccessResult[None]:
                return SuccessResult(None)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        schema: dict[str, pl.DataType] = {'a': pl.Int64(), 'b': pl.String()}
        initial = Success(schema)
        result = execute_output_dry_run(initial, [DummyOutputPlugin({}, tmp_path)])

        assert isinstance(result, Success)
        assert result.unwrap() == schema

    def test_output_dry_run_failure(self, tmp_path: Path) -> None:
        """Test output dry-run with validation failure."""
        from returns.result import Failure as FailureResult

        class FailingOutputPlugin(OutputPlugin):
            def name(self) -> str:
                return 'failing_output'

            def execute(self, df: FrameData) -> FailureResult[Exception]:
                return FailureResult(ValueError('execution error'))

            def dry_run(self, schema: dict[str, pl.DataType]) -> FailureResult[Exception]:
                return FailureResult(ValueError('Invalid output schema'))

        schema: dict[str, pl.DataType] = {'a': pl.Int64()}
        initial = Success(schema)
        result = execute_output_dry_run(initial, [FailingOutputPlugin({}, tmp_path)])

        assert isinstance(result, Failure)
        assert 'Invalid output schema' in str(result.failure())

    def test_output_dry_run_propagate_failure(self, tmp_path: Path) -> None:
        """Test that upstream failure is propagated."""
        from returns.result import Success as SuccessResult

        class DummyOutputPlugin(OutputPlugin):
            def name(self) -> str:
                return 'dummy_output'

            def execute(self, df: FrameData) -> SuccessResult[None]:
                return SuccessResult(None)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        upstream_error = ValueError('upstream error')
        initial = Failure(upstream_error)
        result = execute_output_dry_run(initial, [DummyOutputPlugin({}, tmp_path)])

        assert isinstance(result, Failure)
        assert result.failure() == upstream_error
