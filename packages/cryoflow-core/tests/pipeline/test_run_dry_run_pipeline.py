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
            @property
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
            @property
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
            @property
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
            @property
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

    def test_dry_run_pipeline_label_failures_stay_independent(self, tmp_path: Path) -> None:
        """A failing transform on one label should not block another label's validation."""

        class StockInputPlugin(InputPlugin):
            @property
            def name(self) -> str:
                return 'stock_input'

            def execute(self) -> Success[FrameData]:
                return Success(pl.LazyFrame({'quantity': [1]}))

            def dry_run(self) -> Success[dict[str, pl.DataType]]:
                return Success({'quantity': pl.Int64()})

        class FailingSalesTransformPlugin(TransformPlugin):
            @property
            def name(self) -> str:
                return 'failing_sales_transform'

            def execute(self, df: FrameData) -> Failure[Exception]:
                return Failure(ValueError('execution error'))

            def dry_run(self, schema: dict[str, pl.DataType]) -> Failure[Exception]:
                return Failure(ValueError('sales validation error'))

        class AddFlagPlugin(TransformPlugin):
            @property
            def name(self) -> str:
                return 'add_flag'

            def execute(self, df: FrameData) -> Success[FrameData]:
                return Success(df)

            def dry_run(self, schema: dict[str, pl.DataType]) -> Success[dict[str, pl.DataType]]:
                return Success({**schema, 'flag': pl.Boolean()})

        input_sales = DummyInputPlugin({}, tmp_path, label='sales')
        input_stock = StockInputPlugin({}, tmp_path, label='stock')
        failing_sales = FailingSalesTransformPlugin({}, tmp_path, label='sales')
        add_flag_stock = AddFlagPlugin({}, tmp_path, label='stock')
        output_stock = DummyOutputPlugin({}, tmp_path, label='stock')

        result = run_dry_run_pipeline(
            [input_sales, input_stock],
            [failing_sales, add_flag_stock],
            [output_stock],
        )

        assert isinstance(result, Success)
        assert result.unwrap() == {'quantity': pl.Int64(), 'flag': pl.Boolean()}
