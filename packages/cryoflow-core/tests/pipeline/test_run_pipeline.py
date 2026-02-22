"""Tests for run_pipeline function."""

from pathlib import Path

import polars as pl
from returns.result import Failure, Success

from cryoflow_core.pipeline import run_pipeline
from cryoflow_core.plugin import FrameData, InputPlugin, TransformPlugin

from ..conftest import DummyInputPlugin, DummyOutputPlugin, DummyTransformPlugin


class TestRunPipeline:
    """Tests for complete pipeline execution using InputPlugin."""

    def test_pipeline_success(self, tmp_path: Path) -> None:
        """Test successful end-to-end pipeline with DummyInputPlugin."""
        input_plugin = DummyInputPlugin({}, tmp_path)
        transform_plugin = DummyTransformPlugin({}, tmp_path)
        output_plugin = DummyOutputPlugin({}, tmp_path)

        result = run_pipeline([input_plugin], [transform_plugin], [output_plugin])
        assert isinstance(result, Success)

    def test_pipeline_no_input_plugins(self, tmp_path: Path) -> None:
        """Test pipeline with no input plugins returns Success(None) (empty data_map)."""
        output_plugin = DummyOutputPlugin({}, tmp_path)
        result = run_pipeline([], [], [output_plugin])
        # No input plugins means data_map is empty, output with label 'default' will fail
        assert isinstance(result, Failure)
        assert 'default' in str(result.failure())

    def test_pipeline_no_transform_plugins(self, tmp_path: Path) -> None:
        """Test pipeline with no transform plugins."""
        input_plugin = DummyInputPlugin({}, tmp_path)
        output_plugin = DummyOutputPlugin({}, tmp_path)

        result = run_pipeline([input_plugin], [], [output_plugin])
        assert isinstance(result, Success)

    def test_pipeline_input_failure(self, tmp_path: Path) -> None:
        """Test pipeline when input plugin fails."""
        from returns.result import Failure as FailureResult

        class FailingInputPlugin(InputPlugin):
            def name(self) -> str:
                return 'failing_input'

            def execute(self) -> FailureResult[Exception]:
                return FailureResult(FileNotFoundError('file not found'))

            def dry_run(self) -> FailureResult[Exception]:
                return FailureResult(FileNotFoundError('file not found'))

        input_plugin = FailingInputPlugin({}, tmp_path)
        output_plugin = DummyOutputPlugin({}, tmp_path)

        result = run_pipeline([input_plugin], [], [output_plugin])
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), FileNotFoundError)

    def test_pipeline_transform_fails(self, tmp_path: Path) -> None:
        """Test pipeline when transform plugin fails."""
        from returns.result import Failure as FailureResult

        class FailingTransformPlugin(TransformPlugin):
            def name(self) -> str:
                return 'failing_transform'

            def execute(self, df: FrameData) -> FailureResult[Exception]:
                return FailureResult(ValueError('intentional failure'))

            def dry_run(self, schema: dict[str, pl.DataType]) -> FailureResult[Exception]:
                return FailureResult(ValueError('intentional dry_run failure'))

        input_plugin = DummyInputPlugin({}, tmp_path)
        transform_plugin = FailingTransformPlugin({}, tmp_path)
        output_plugin = DummyOutputPlugin({}, tmp_path)

        result = run_pipeline([input_plugin], [transform_plugin], [output_plugin])
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), ValueError)
