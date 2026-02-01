"""Tests for the data processing pipeline."""

from pathlib import Path
from tempfile import TemporaryDirectory

import polars as pl
import pytest
from returns.result import Failure, Success

from cryoflow_core.pipeline import (
    _detect_format,
    execute_output,
    execute_transform_chain,
    load_data,
    run_pipeline,
)


class TestDetectFormat:
    """Tests for file format detection."""

    def test_parquet_extension(self) -> None:
        """Test detection of .parquet extension."""
        path = Path('data.parquet')
        assert _detect_format(path) == 'parquet'

    def test_ipc_extension(self) -> None:
        """Test detection of .ipc extension."""
        path = Path('data.ipc')
        assert _detect_format(path) == 'ipc'

    def test_arrow_extension(self) -> None:
        """Test detection of .arrow extension."""
        path = Path('data.arrow')
        assert _detect_format(path) == 'ipc'

    def test_uppercase_extension(self) -> None:
        """Test detection with uppercase extension."""
        path = Path('data.PARQUET')
        assert _detect_format(path) == 'parquet'

    def test_unknown_extension(self) -> None:
        """Test detection of unsupported extension."""
        path = Path('data.csv')
        assert _detect_format(path) is None

    def test_no_extension(self) -> None:
        """Test detection with no extension."""
        path = Path('datafile')
        assert _detect_format(path) is None


class TestLoadData:
    """Tests for data loading."""

    def test_load_parquet_success(self) -> None:
        """Test successful Parquet file loading."""
        with TemporaryDirectory() as tmpdir:
            # Create a test Parquet file
            test_file = Path(tmpdir) / 'test.parquet'
            df = pl.DataFrame({'a': [1, 2, 3], 'b': ['x', 'y', 'z']})
            df.write_parquet(test_file)

            result = load_data(test_file)
            assert isinstance(result, Success)
            loaded = result.unwrap()
            assert isinstance(loaded, pl.LazyFrame)
            assert loaded.collect().to_dict(as_series=False) == {
                'a': [1, 2, 3],
                'b': ['x', 'y', 'z'],
            }

    def test_load_ipc_success(self) -> None:
        """Test successful IPC file loading."""
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / 'test.ipc'
            df = pl.DataFrame({'a': [1, 2, 3], 'b': ['x', 'y', 'z']})
            df.write_ipc(test_file)

            result = load_data(test_file)
            assert isinstance(result, Success)
            loaded = result.unwrap()
            assert isinstance(loaded, pl.LazyFrame)

    def test_load_file_not_found(self) -> None:
        """Test error when file does not exist."""
        result = load_data(Path('/nonexistent/path/file.parquet'))
        assert isinstance(result, Failure)
        error = result.failure()
        assert isinstance(error, FileNotFoundError)

    def test_load_unsupported_format(self) -> None:
        """Test error when file format is unsupported."""
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / 'test.csv'
            test_file.write_text('a,b\n1,x\n')
            result = load_data(test_file)
            assert isinstance(result, Failure)
            error = result.failure()
            assert isinstance(error, ValueError)
            assert 'Unsupported file format' in str(error)


class TestExecuteTransformChain:
    """Tests for transformation plugin chain execution."""

    def test_empty_plugin_chain(self, sample_lazyframe) -> None:
        """Test with no transformation plugins."""
        initial = Success(sample_lazyframe)
        result = execute_transform_chain(initial, [])
        assert isinstance(result, Success)
        # Can't compare LazyFrames directly, just verify it's a Success
        assert result.unwrap() is sample_lazyframe

    def test_single_plugin_success(self, sample_lazyframe) -> None:
        """Test with single successful plugin."""
        from cryoflow_core.plugin import FrameData, TransformPlugin
        from returns.result import Success as SuccessResult

        class DummyTransformPlugin(TransformPlugin):
            def name(self) -> str:
                return 'dummy_transform'

            def execute(self, df: FrameData) -> SuccessResult[FrameData]:
                return SuccessResult(df)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        plugin = DummyTransformPlugin({})
        initial = Success(sample_lazyframe)
        result = execute_transform_chain(initial, [plugin])
        assert isinstance(result, Success)
        assert result.unwrap() is sample_lazyframe

    def test_multiple_plugins_success(self, sample_lazyframe) -> None:
        """Test with multiple successful plugins."""
        from cryoflow_core.plugin import FrameData, TransformPlugin
        from returns.result import Success as SuccessResult

        class DummyTransformPlugin(TransformPlugin):
            def name(self) -> str:
                return 'dummy_transform'

            def execute(self, df: FrameData) -> SuccessResult[FrameData]:
                return SuccessResult(df)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        plugins = [DummyTransformPlugin({}), DummyTransformPlugin({})]
        initial = Success(sample_lazyframe)
        result = execute_transform_chain(initial, plugins)
        assert isinstance(result, Success)

    def test_chain_stops_on_failure(self, sample_lazyframe) -> None:
        """Test that chain stops when a plugin fails."""
        from cryoflow_core.plugin import FrameData, TransformPlugin
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
            DummyTransformPlugin({}),
            FailingTransformPlugin({}),
            DummyTransformPlugin({}),
        ]
        initial = Success(sample_lazyframe)
        result = execute_transform_chain(initial, plugins)
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), ValueError)

    def test_propagate_initial_failure(self, sample_lazyframe) -> None:
        """Test that initial Failure is propagated."""
        from cryoflow_core.plugin import FrameData, TransformPlugin
        from returns.result import Success as SuccessResult

        class DummyTransformPlugin(TransformPlugin):
            def name(self) -> str:
                return 'dummy_transform'

            def execute(self, df: FrameData) -> SuccessResult[FrameData]:
                return SuccessResult(df)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        plugins = [DummyTransformPlugin({}), DummyTransformPlugin({})]
        initial_error = ValueError('initial error')
        initial = Failure(initial_error)
        result = execute_transform_chain(initial, plugins)
        assert isinstance(result, Failure)
        assert result.failure() == initial_error


class TestExecuteOutput:
    """Tests for output plugin execution."""

    def test_output_success_data(self, sample_lazyframe) -> None:
        """Test output with successful data."""
        from cryoflow_core.plugin import FrameData, OutputPlugin
        from returns.result import Success as SuccessResult

        class DummyOutputPlugin(OutputPlugin):
            def name(self) -> str:
                return 'dummy_output'

            def execute(self, df: FrameData) -> SuccessResult[None]:
                return SuccessResult(None)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        plugin = DummyOutputPlugin({})
        data = Success(sample_lazyframe)
        result = execute_output(data, plugin)
        assert isinstance(result, Success)

    def test_output_failure_data(self) -> None:
        """Test output with failed data (should not execute plugin)."""
        from cryoflow_core.plugin import FrameData, OutputPlugin
        from returns.result import Success as SuccessResult

        class DummyOutputPlugin(OutputPlugin):
            def name(self) -> str:
                return 'dummy_output'

            def execute(self, df: FrameData) -> SuccessResult[None]:
                return SuccessResult(None)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        plugin = DummyOutputPlugin({})
        error = ValueError('data processing error')
        data = Failure(error)
        result = execute_output(data, plugin)
        assert isinstance(result, Failure)
        assert result.failure() == error


class TestRunPipeline:
    """Tests for complete pipeline execution."""

    def test_pipeline_success(self) -> None:
        """Test successful end-to-end pipeline."""
        from cryoflow_core.plugin import FrameData, OutputPlugin, TransformPlugin
        from returns.result import Success as SuccessResult

        class DummyTransformPlugin(TransformPlugin):
            def name(self) -> str:
                return 'dummy_transform'

            def execute(self, df: FrameData) -> SuccessResult[FrameData]:
                return SuccessResult(df)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        class DummyOutputPlugin(OutputPlugin):
            def name(self) -> str:
                return 'dummy_output'

            def execute(self, df: FrameData) -> SuccessResult[None]:
                return SuccessResult(None)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        with TemporaryDirectory() as tmpdir:
            # Create input file
            input_file = Path(tmpdir) / 'input.parquet'
            df = pl.DataFrame({'a': [1, 2, 3], 'b': ['x', 'y', 'z']})
            df.write_parquet(input_file)

            # Run pipeline
            transform_plugins = [DummyTransformPlugin({})]
            output_plugin = DummyOutputPlugin({})
            result = run_pipeline(input_file, transform_plugins, output_plugin)

            assert isinstance(result, Success)

    def test_pipeline_input_not_found(self) -> None:
        """Test pipeline with missing input file."""
        from cryoflow_core.plugin import FrameData, OutputPlugin, TransformPlugin
        from returns.result import Success as SuccessResult

        class DummyTransformPlugin(TransformPlugin):
            def name(self) -> str:
                return 'dummy_transform'

            def execute(self, df: FrameData) -> SuccessResult[FrameData]:
                return SuccessResult(df)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        class DummyOutputPlugin(OutputPlugin):
            def name(self) -> str:
                return 'dummy_output'

            def execute(self, df: FrameData) -> SuccessResult[None]:
                return SuccessResult(None)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        input_file = Path('/nonexistent/path/file.parquet')
        transform_plugins = [DummyTransformPlugin({})]
        output_plugin = DummyOutputPlugin({})
        result = run_pipeline(input_file, transform_plugins, output_plugin)

        assert isinstance(result, Failure)

    def test_pipeline_transform_fails(self) -> None:
        """Test pipeline when transform plugin fails."""
        from cryoflow_core.plugin import FrameData, OutputPlugin, TransformPlugin
        from returns.result import Failure as FailureResult, Success as SuccessResult

        class FailingTransformPlugin(TransformPlugin):
            def name(self) -> str:
                return 'failing_transform'

            def execute(self, df: FrameData) -> FailureResult[Exception]:
                return FailureResult(ValueError('intentional failure'))

            def dry_run(self, schema: dict[str, pl.DataType]) -> FailureResult[Exception]:
                return FailureResult(ValueError('intentional dry_run failure'))

        class DummyOutputPlugin(OutputPlugin):
            def name(self) -> str:
                return 'dummy_output'

            def execute(self, df: FrameData) -> SuccessResult[None]:
                return SuccessResult(None)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        with TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / 'input.parquet'
            df = pl.DataFrame({'a': [1, 2, 3]})
            df.write_parquet(input_file)

            transform_plugins = [FailingTransformPlugin({})]
            output_plugin = DummyOutputPlugin({})
            result = run_pipeline(input_file, transform_plugins, output_plugin)

            assert isinstance(result, Failure)
            assert isinstance(result.failure(), ValueError)
