"""Tests for execute_dry_run_chain function."""

from pathlib import Path

import polars as pl
from returns.result import Failure, Success

from cryoflow_core.pipeline import execute_dry_run_chain
from cryoflow_core.plugin import FrameData, TransformPlugin


class TestExecuteDryRunChain:
    """Tests for dry-run transformation chain execution."""

    def test_empty_plugin_chain(self) -> None:
        """Test dry-run with no transformation plugins."""
        schema: dict[str, pl.DataType] = {'a': pl.Int64(), 'b': pl.String()}
        initial = Success(schema)
        result = execute_dry_run_chain(initial, [])

        assert isinstance(result, Success)
        assert result.unwrap() == schema

    def test_single_plugin_success(self, tmp_path: Path) -> None:
        """Test dry-run with single successful plugin."""
        from returns.result import Success as SuccessResult

        class DummyTransformPlugin(TransformPlugin):
            def name(self) -> str:
                return 'dummy_transform'

            def execute(self, df: FrameData) -> SuccessResult[FrameData]:
                return SuccessResult(df)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        schema: dict[str, pl.DataType] = {'a': pl.Int64()}
        initial = Success(schema)
        result = execute_dry_run_chain(initial, [DummyTransformPlugin({}, tmp_path)])

        assert isinstance(result, Success)
        assert result.unwrap() == schema

    def test_plugin_validation_failure(self, tmp_path: Path) -> None:
        """Test dry-run where plugin validation fails."""
        from returns.result import Failure as FailureResult

        class FailingValidationPlugin(TransformPlugin):
            def name(self) -> str:
                return 'failing_validation'

            def execute(self, df: FrameData) -> FailureResult[Exception]:
                return FailureResult(ValueError('execution error'))

            def dry_run(self, schema: dict[str, pl.DataType]) -> FailureResult[Exception]:
                return FailureResult(ValueError("Column 'missing_col' not found"))

        schema: dict[str, pl.DataType] = {'a': pl.Int64()}
        initial = Success(schema)
        result = execute_dry_run_chain(initial, [FailingValidationPlugin({}, tmp_path)])

        assert isinstance(result, Failure)
        assert 'missing_col' in str(result.failure())

    def test_propagate_initial_failure(self, tmp_path: Path) -> None:
        """Test that initial Failure is propagated."""
        from returns.result import Success as SuccessResult

        class DummyPlugin(TransformPlugin):
            def name(self) -> str:
                return 'dummy'

            def execute(self, df: FrameData) -> SuccessResult[FrameData]:
                return SuccessResult(df)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        initial_error = ValueError('initial error')
        initial = Failure(initial_error)
        result = execute_dry_run_chain(initial, [DummyPlugin({}, tmp_path)])

        assert isinstance(result, Failure)
        assert result.failure() == initial_error
