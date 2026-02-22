"""Tests for execute_transform_chain function."""

from pathlib import Path

import polars as pl
from returns.result import Failure, Success

from cryoflow_core.pipeline import execute_transform_chain
from cryoflow_core.plugin import FrameData, TransformPlugin


class TestExecuteTransformChain:
    """Tests for transformation plugin chain execution."""

    def test_empty_plugin_chain(self, sample_lazyframe) -> None:
        """Test with no transformation plugins."""
        initial = Success(sample_lazyframe)
        result = execute_transform_chain(initial, [])
        assert isinstance(result, Success)
        assert result.unwrap() is sample_lazyframe

    def test_single_plugin_success(self, sample_lazyframe, tmp_path: Path) -> None:
        """Test with single successful plugin."""
        from returns.result import Success as SuccessResult

        class DummyTransformPlugin(TransformPlugin):
            def name(self) -> str:
                return 'dummy_transform'

            def execute(self, df: FrameData) -> SuccessResult[FrameData]:
                return SuccessResult(df)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        plugin = DummyTransformPlugin({}, tmp_path)
        initial = Success(sample_lazyframe)
        result = execute_transform_chain(initial, [plugin])
        assert isinstance(result, Success)
        assert result.unwrap() is sample_lazyframe

    def test_multiple_plugins_success(self, sample_lazyframe, tmp_path: Path) -> None:
        """Test with multiple successful plugins."""
        from returns.result import Success as SuccessResult

        class DummyTransformPlugin(TransformPlugin):
            def name(self) -> str:
                return 'dummy_transform'

            def execute(self, df: FrameData) -> SuccessResult[FrameData]:
                return SuccessResult(df)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        plugins: list[TransformPlugin] = [DummyTransformPlugin({}, tmp_path), DummyTransformPlugin({}, tmp_path)]
        initial = Success(sample_lazyframe)
        result = execute_transform_chain(initial, plugins)
        assert isinstance(result, Success)

    def test_chain_stops_on_failure(self, sample_lazyframe, tmp_path: Path) -> None:
        """Test that chain stops when a plugin fails."""
        from returns.result import Failure as FailureResult, Success as SuccessResult

        class DummyTransformPlugin(TransformPlugin):
            def name(self) -> str:
                return 'dummy_transform'

            def execute(self, df: FrameData) -> SuccessResult[FrameData]:
                return SuccessResult(df)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        class FailingTransformPlugin(TransformPlugin):
            def name(self) -> str:
                return 'failing_transform'

            def execute(self, df: FrameData) -> FailureResult[Exception]:
                return FailureResult(ValueError('intentional failure'))

            def dry_run(self, schema: dict[str, pl.DataType]) -> FailureResult[Exception]:
                return FailureResult(ValueError('intentional dry_run failure'))

        plugins = [
            DummyTransformPlugin({}, tmp_path),
            FailingTransformPlugin({}, tmp_path),
            DummyTransformPlugin({}, tmp_path),
        ]
        initial = Success(sample_lazyframe)
        result = execute_transform_chain(initial, plugins)
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), ValueError)

    def test_propagate_initial_failure(self, tmp_path: Path) -> None:
        """Test that initial Failure is propagated."""
        from returns.result import Success as SuccessResult

        class DummyTransformPlugin(TransformPlugin):
            def name(self) -> str:
                return 'dummy_transform'

            def execute(self, df: FrameData) -> SuccessResult[FrameData]:
                return SuccessResult(df)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        plugins: list[TransformPlugin] = [DummyTransformPlugin({}, tmp_path), DummyTransformPlugin({}, tmp_path)]
        initial_error = ValueError('initial error')
        initial = Failure(initial_error)
        result = execute_transform_chain(initial, plugins)
        assert isinstance(result, Failure)
        assert result.failure() == initial_error
