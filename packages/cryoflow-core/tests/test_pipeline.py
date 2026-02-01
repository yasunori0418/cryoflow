"""Tests for the data processing pipeline."""

from pathlib import Path
from tempfile import TemporaryDirectory

import polars as pl
from returns.result import Failure, Success

from cryoflow_core.pipeline import (
    _detect_format,
    execute_output,
    execute_transform_chain,
    extract_schema,  # noqa: F401
    execute_dry_run_chain,  # noqa: F401
    execute_output_dry_run,  # noqa: F401
    load_data,
    run_pipeline,
    run_dry_run_pipeline,  # noqa: F401
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


class TestExtractSchema:
    """Tests for schema extraction."""

    def test_extract_schema_from_lazyframe(self) -> None:
        """Test schema extraction from LazyFrame."""
        df = pl.DataFrame({'a': [1, 2, 3], 'b': ['x', 'y', 'z']})
        lazy_df = df.lazy()
        result = extract_schema(lazy_df)

        assert isinstance(result, Success)
        schema = result.unwrap()
        assert 'a' in schema
        assert 'b' in schema
        assert schema['a'] == pl.Int64
        assert schema['b'] == pl.String

    def test_extract_schema_from_dataframe(self) -> None:
        """Test schema extraction from DataFrame."""
        df = pl.DataFrame({'x': [1.0, 2.0], 'y': [10, 20]})
        result = extract_schema(df)

        assert isinstance(result, Success)
        schema = result.unwrap()
        assert 'x' in schema
        assert 'y' in schema
        assert schema['x'] == pl.Float64
        assert schema['y'] == pl.Int64

    def test_extract_schema_empty_frame(self) -> None:
        """Test schema extraction from empty DataFrame."""
        df = pl.DataFrame({'col1': pl.Series([], dtype=pl.Int32), 'col2': pl.Series([], dtype=pl.String)})
        result = extract_schema(df)

        assert isinstance(result, Success)
        schema = result.unwrap()
        assert 'col1' in schema
        assert 'col2' in schema
        assert schema['col1'] == pl.Int32
        assert schema['col2'] == pl.String


class TestExecuteDryRunChain:
    """Tests for dry-run transformation chain execution."""

    def test_empty_plugin_chain(self) -> None:
        """Test dry-run with no transformation plugins."""
        schema = {'a': pl.Int64, 'b': pl.String}
        initial = Success(schema)
        result = execute_dry_run_chain(initial, [])

        assert isinstance(result, Success)
        assert result.unwrap() == schema

    def test_single_plugin_success(self) -> None:
        """Test dry-run with single successful plugin."""
        from cryoflow_core.plugin import TransformPlugin
        from returns.result import Success as SuccessResult

        class DummyTransformPlugin(TransformPlugin):
            def name(self) -> str:
                return 'dummy_transform'

            def execute(self, df):
                return SuccessResult(df)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        schema = {'a': pl.Int64}
        initial = Success(schema)
        result = execute_dry_run_chain(initial, [DummyTransformPlugin({})])

        assert isinstance(result, Success)
        assert result.unwrap() == schema

    def test_multiple_plugins_success(self) -> None:
        """Test dry-run with multiple successful plugins."""
        from cryoflow_core.plugin import TransformPlugin
        from returns.result import Success as SuccessResult

        class DummyTransformPlugin(TransformPlugin):
            def name(self) -> str:
                return 'dummy_transform'

            def execute(self, df):
                return SuccessResult(df)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        schema = {'a': pl.Int64, 'b': pl.String}
        initial = Success(schema)
        plugins = [DummyTransformPlugin({}), DummyTransformPlugin({})]
        result = execute_dry_run_chain(initial, plugins)

        assert isinstance(result, Success)
        assert result.unwrap() == schema

    def test_plugin_modifies_schema(self) -> None:
        """Test dry-run where plugin modifies schema."""
        from cryoflow_core.plugin import TransformPlugin
        from returns.result import Success as SuccessResult

        class SchemaModifyingPlugin(TransformPlugin):
            def name(self) -> str:
                return 'schema_modifier'

            def execute(self, df):
                return SuccessResult(df)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                # Add a new column to schema
                new_schema = dict(schema)
                new_schema['new_col'] = pl.Float64
                return SuccessResult(new_schema)

        schema = {'a': pl.Int64}
        initial = Success(schema)
        result = execute_dry_run_chain(initial, [SchemaModifyingPlugin({})])

        assert isinstance(result, Success)
        final_schema = result.unwrap()
        assert 'a' in final_schema
        assert 'new_col' in final_schema

    def test_plugin_validation_failure(self) -> None:
        """Test dry-run where plugin validation fails."""
        from cryoflow_core.plugin import TransformPlugin
        from returns.result import Failure as FailureResult

        class FailingValidationPlugin(TransformPlugin):
            def name(self) -> str:
                return 'failing_validation'

            def execute(self, df):
                return FailureResult(ValueError('execution error'))

            def dry_run(self, schema: dict[str, pl.DataType]) -> FailureResult[Exception]:
                return FailureResult(ValueError("Column 'missing_col' not found"))

        schema = {'a': pl.Int64}
        initial = Success(schema)
        result = execute_dry_run_chain(initial, [FailingValidationPlugin({})])

        assert isinstance(result, Failure)
        assert 'missing_col' in str(result.failure())

    def test_chain_stops_on_plugin_failure(self) -> None:
        """Test that chain stops at first plugin failure."""
        from cryoflow_core.plugin import TransformPlugin
        from returns.result import Failure as FailureResult, Success as SuccessResult

        class FailingPlugin(TransformPlugin):
            def name(self) -> str:
                return 'failing'

            def execute(self, df):
                return SuccessResult(df)

            def dry_run(self, schema: dict[str, pl.DataType]) -> FailureResult[Exception]:
                return FailureResult(ValueError('validation error'))

        class SuccessPlugin(TransformPlugin):
            def __init__(self):
                super().__init__({})
                self.was_called = False

            def name(self) -> str:
                return 'success'

            def execute(self, df):
                return SuccessResult(df)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                self.was_called = True
                return SuccessResult(schema)

        schema = {'a': pl.Int64}
        initial = Success(schema)
        success_plugin = SuccessPlugin()
        plugins = [FailingPlugin({}), success_plugin]
        result = execute_dry_run_chain(initial, plugins)

        assert isinstance(result, Failure)
        assert not success_plugin.was_called

    def test_propagate_initial_failure(self) -> None:
        """Test that initial Failure is propagated."""
        from cryoflow_core.plugin import TransformPlugin
        from returns.result import Success as SuccessResult

        class DummyPlugin(TransformPlugin):
            def name(self) -> str:
                return 'dummy'

            def execute(self, df):
                return SuccessResult(df)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        initial_error = ValueError('initial error')
        initial = Failure(initial_error)
        result = execute_dry_run_chain(initial, [DummyPlugin({})])

        assert isinstance(result, Failure)
        assert result.failure() == initial_error


class TestExecuteOutputDryRun:
    """Tests for output plugin dry-run execution."""

    def test_output_dry_run_success(self) -> None:
        """Test output dry-run with successful validation."""
        from cryoflow_core.plugin import OutputPlugin
        from returns.result import Success as SuccessResult

        class DummyOutputPlugin(OutputPlugin):
            def name(self) -> str:
                return 'dummy_output'

            def execute(self, df):
                return SuccessResult(None)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        schema = {'a': pl.Int64, 'b': pl.String}
        initial = Success(schema)
        result = execute_output_dry_run(initial, DummyOutputPlugin({}))

        assert isinstance(result, Success)
        assert result.unwrap() == schema

    def test_output_dry_run_failure(self) -> None:
        """Test output dry-run with validation failure."""
        from cryoflow_core.plugin import OutputPlugin
        from returns.result import Failure as FailureResult

        class FailingOutputPlugin(OutputPlugin):
            def name(self) -> str:
                return 'failing_output'

            def execute(self, df):
                return FailureResult(ValueError('execution error'))

            def dry_run(self, schema: dict[str, pl.DataType]) -> FailureResult[Exception]:
                return FailureResult(ValueError('Invalid output schema'))

        schema = {'a': pl.Int64}
        initial = Success(schema)
        result = execute_output_dry_run(initial, FailingOutputPlugin({}))

        assert isinstance(result, Failure)
        assert 'Invalid output schema' in str(result.failure())

    def test_output_dry_run_propagate_failure(self) -> None:
        """Test that upstream failure is propagated."""
        from cryoflow_core.plugin import OutputPlugin
        from returns.result import Success as SuccessResult

        class DummyOutputPlugin(OutputPlugin):
            def name(self) -> str:
                return 'dummy_output'

            def execute(self, df):
                return SuccessResult(None)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        upstream_error = ValueError('upstream error')
        initial = Failure(upstream_error)
        result = execute_output_dry_run(initial, DummyOutputPlugin({}))

        assert isinstance(result, Failure)
        assert result.failure() == upstream_error


class TestRunDryRunPipeline:
    """Tests for complete dry-run pipeline execution."""

    def test_dry_run_pipeline_success(self) -> None:
        """Test successful dry-run pipeline."""
        from cryoflow_core.plugin import OutputPlugin, TransformPlugin
        from returns.result import Success as SuccessResult

        class DummyTransformPlugin(TransformPlugin):
            def name(self) -> str:
                return 'dummy_transform'

            def execute(self, df):
                return SuccessResult(df)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        class DummyOutputPlugin(OutputPlugin):
            def name(self) -> str:
                return 'dummy_output'

            def execute(self, df):
                return SuccessResult(None)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        with TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / 'input.parquet'
            df = pl.DataFrame({'a': [1, 2, 3], 'b': ['x', 'y', 'z']})
            df.write_parquet(input_file)

            result = run_dry_run_pipeline(
                input_file,
                [DummyTransformPlugin({})],
                DummyOutputPlugin({})
            )

            assert isinstance(result, Success)
            schema = result.unwrap()
            assert 'a' in schema
            assert 'b' in schema

    def test_dry_run_pipeline_input_not_found(self) -> None:
        """Test dry-run with missing input file."""
        from cryoflow_core.plugin import OutputPlugin, TransformPlugin
        from returns.result import Success as SuccessResult

        class DummyTransformPlugin(TransformPlugin):
            def name(self) -> str:
                return 'dummy_transform'

            def execute(self, df):
                return SuccessResult(df)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        class DummyOutputPlugin(OutputPlugin):
            def name(self) -> str:
                return 'dummy_output'

            def execute(self, df):
                return SuccessResult(None)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        result = run_dry_run_pipeline(
            Path('/nonexistent/path/file.parquet'),
            [DummyTransformPlugin({})],
            DummyOutputPlugin({})
        )

        assert isinstance(result, Failure)
        assert isinstance(result.failure(), FileNotFoundError)

    def test_dry_run_pipeline_transform_validation_fails(self) -> None:
        """Test dry-run when transform validation fails."""
        from cryoflow_core.plugin import OutputPlugin, TransformPlugin
        from returns.result import Failure as FailureResult, Success as SuccessResult

        class FailingTransformPlugin(TransformPlugin):
            def name(self) -> str:
                return 'failing_transform'

            def execute(self, df):
                return FailureResult(ValueError('execution error'))

            def dry_run(self, schema: dict[str, pl.DataType]) -> FailureResult[Exception]:
                return FailureResult(ValueError("Column 'missing_col' not found"))

        class DummyOutputPlugin(OutputPlugin):
            def name(self) -> str:
                return 'dummy_output'

            def execute(self, df):
                return SuccessResult(None)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        with TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / 'input.parquet'
            df = pl.DataFrame({'a': [1, 2, 3]})
            df.write_parquet(input_file)

            result = run_dry_run_pipeline(
                input_file,
                [FailingTransformPlugin({})],
                DummyOutputPlugin({})
            )

            assert isinstance(result, Failure)
            assert 'missing_col' in str(result.failure())

    def test_dry_run_pipeline_output_validation_fails(self) -> None:
        """Test dry-run when output validation fails."""
        from cryoflow_core.plugin import OutputPlugin, TransformPlugin
        from returns.result import Failure as FailureResult, Success as SuccessResult

        class DummyTransformPlugin(TransformPlugin):
            def name(self) -> str:
                return 'dummy_transform'

            def execute(self, df):
                return SuccessResult(df)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        class FailingOutputPlugin(OutputPlugin):
            def name(self) -> str:
                return 'failing_output'

            def execute(self, df):
                return SuccessResult(None)

            def dry_run(self, schema: dict[str, pl.DataType]) -> FailureResult[Exception]:
                return FailureResult(ValueError('Invalid output format'))

        with TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / 'input.parquet'
            df = pl.DataFrame({'a': [1, 2, 3]})
            df.write_parquet(input_file)

            result = run_dry_run_pipeline(
                input_file,
                [DummyTransformPlugin({})],
                FailingOutputPlugin({})
            )

            assert isinstance(result, Failure)
            assert 'Invalid output format' in str(result.failure())
