"""Tests for run_dry_run_pipeline function."""

from pathlib import Path

import polars as pl
from returns.result import Failure, Success

from cryoflow_core.pipeline import run_dry_run_pipeline
from cryoflow_core.plugin import FrameData, InputPlugin, OutputPlugin, TransformPlugin

from ..conftest import DummyInputPlugin, DummyOutputPlugin, DummyTransformPlugin


class TestRunDryRunPipeline:
    """Tests for complete dry-run pipeline execution using InputPlugin."""

    def test_dry_run_pipeline_success(self, tmp_path: Path) -> None:
        """Test successful dry-run pipeline with DummyInputPlugin."""
        input_plugin = DummyInputPlugin({}, tmp_path)
        transform_plugin = DummyTransformPlugin({}, tmp_path)
        output_plugin = DummyOutputPlugin({}, tmp_path)

        result = run_dry_run_pipeline([input_plugin], [transform_plugin], [output_plugin])

        assert isinstance(result, Success)
        schema = result.unwrap()
        assert 'a' in schema
        assert 'b' in schema

    def test_dry_run_pipeline_input_failure(self, tmp_path: Path) -> None:
        """Test dry-run when input dry_run fails."""
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

        result = run_dry_run_pipeline([input_plugin], [], [output_plugin])

        assert isinstance(result, Failure)
        assert isinstance(result.failure(), FileNotFoundError)

    def test_dry_run_pipeline_transform_validation_fails(self, tmp_path: Path) -> None:
        """Test dry-run when transform validation fails."""
        from returns.result import Failure as FailureResult

        class FailingTransformPlugin(TransformPlugin):
            def name(self) -> str:
                return 'failing_transform'

            def execute(self, df: FrameData) -> FailureResult[Exception]:
                return FailureResult(ValueError('execution error'))

            def dry_run(self, schema: dict[str, pl.DataType]) -> FailureResult[Exception]:
                return FailureResult(ValueError("Column 'missing_col' not found"))

        input_plugin = DummyInputPlugin({}, tmp_path)
        transform_plugin = FailingTransformPlugin({}, tmp_path)
        output_plugin = DummyOutputPlugin({}, tmp_path)

        result = run_dry_run_pipeline([input_plugin], [transform_plugin], [output_plugin])

        assert isinstance(result, Failure)
        assert 'missing_col' in str(result.failure())

    def test_dry_run_pipeline_output_validation_fails(self, tmp_path: Path) -> None:
        """Test dry-run when output validation fails."""
        from returns.result import Failure as FailureResult
        from returns.result import Success as SuccessResult

        class FailingOutputPlugin(OutputPlugin):
            def name(self) -> str:
                return 'failing_output'

            def execute(self, df: FrameData) -> SuccessResult[None]:
                return SuccessResult(None)

            def dry_run(self, schema: dict[str, pl.DataType]) -> FailureResult[Exception]:
                return FailureResult(ValueError('Invalid output format'))

        input_plugin = DummyInputPlugin({}, tmp_path)
        output_plugin = FailingOutputPlugin({}, tmp_path)

        result = run_dry_run_pipeline([input_plugin], [], [output_plugin])

        assert isinstance(result, Failure)
        assert 'Invalid output format' in str(result.failure())

    def test_dry_run_pipeline_multi_label_routes_by_label(self, tmp_path: Path) -> None:
        """Two labeled inputs with plugins on one label should return that label's schema."""

        class SalesInputPlugin(InputPlugin):
            def name(self) -> str:
                return 'sales_input'

            def execute(self) -> Success[FrameData]:
                return Success(pl.LazyFrame({'amount': [1]}))

            def dry_run(self) -> Success[dict[str, pl.DataType]]:
                return Success({'amount': pl.Int64()})

        input_default = DummyInputPlugin({}, tmp_path, label='default')
        input_sales = SalesInputPlugin({}, tmp_path, label='sales')
        transform_sales = DummyTransformPlugin({}, tmp_path, label='sales')
        output_sales = DummyOutputPlugin({}, tmp_path, label='sales')

        result = run_dry_run_pipeline([input_default, input_sales], [transform_sales], [output_sales])

        assert isinstance(result, Success)
        assert result.unwrap() == {'amount': pl.Int64()}

    def test_dry_run_pipeline_transform_unknown_label(self, tmp_path: Path) -> None:
        """Transform plugin referencing an unknown label should fail with KeyError."""
        input_plugin = DummyInputPlugin({}, tmp_path)
        transform_plugin = DummyTransformPlugin({}, tmp_path, label='nonexistent')
        output_plugin = DummyOutputPlugin({}, tmp_path, label='nonexistent')

        result = run_dry_run_pipeline([input_plugin], [transform_plugin], [output_plugin])

        assert isinstance(result, Failure)
        assert isinstance(result.failure(), KeyError)

    def test_dry_run_pipeline_output_unknown_label(self, tmp_path: Path) -> None:
        """Output plugin referencing an unknown label should fail with KeyError."""
        input_plugin = DummyInputPlugin({}, tmp_path)
        output_plugin = DummyOutputPlugin({}, tmp_path, label='nonexistent')

        result = run_dry_run_pipeline([input_plugin], [], [output_plugin])

        assert isinstance(result, Failure)
        assert isinstance(result.failure(), KeyError)
        assert 'nonexistent' in str(result.failure())

    def test_dry_run_pipeline_without_output_plugins(self, tmp_path: Path) -> None:
        """No output plugin should return the transformed 'default' schema."""
        input_plugin = DummyInputPlugin({}, tmp_path)
        transform_plugin = DummyTransformPlugin({}, tmp_path)

        result = run_dry_run_pipeline([input_plugin], [transform_plugin], [])

        assert isinstance(result, Success)
        assert result.unwrap() == {'a': pl.Int64(), 'b': pl.String()}
