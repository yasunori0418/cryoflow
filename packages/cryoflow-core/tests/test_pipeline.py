"""Tests for the data processing pipeline."""

from pathlib import Path

import polars as pl
from returns.result import Failure, Result, Success

from cryoflow_core.pipeline import (
    LabeledDataMap,
    execute_output,
    execute_transform_chain,
    extract_schema,  # noqa: F401
    execute_dry_run_chain,  # noqa: F401
    execute_output_dry_run,  # noqa: F401
    run_pipeline,
    run_dry_run_pipeline,  # noqa: F401
    _execute_labeled_transform_chain,
    _execute_labeled_output,
)

from .conftest import DummyInputPlugin, DummyOutputPlugin, DummyTransformPlugin


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
        from cryoflow_core.plugin import FrameData, TransformPlugin
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
        from cryoflow_core.plugin import FrameData, TransformPlugin
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
        from cryoflow_core.plugin import FrameData, TransformPlugin
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


class TestExecuteOutput:
    """Tests for output plugin execution."""

    def test_output_success_data(self, sample_lazyframe, tmp_path: Path) -> None:
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

        plugin = DummyOutputPlugin({}, tmp_path)
        data = Success(sample_lazyframe)
        result = execute_output(data, [plugin])
        assert isinstance(result, Success)

    def test_output_failure_data(self, tmp_path: Path) -> None:
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

        plugin = DummyOutputPlugin({}, tmp_path)
        error = ValueError('data processing error')
        data = Failure(error)
        result = execute_output(data, [plugin])
        assert isinstance(result, Failure)
        assert result.failure() == error

    def test_output_empty_plugins(self, sample_lazyframe) -> None:
        """Test output with empty plugin list returns Success(None)."""
        data = Success(sample_lazyframe)
        result = execute_output(data, [])
        assert isinstance(result, Success)

    def test_multiple_output_plugins_all_succeed(self, sample_lazyframe, tmp_path: Path) -> None:
        """Test that all output plugins are executed when data succeeds."""
        from cryoflow_core.plugin import FrameData, OutputPlugin
        from returns.result import Success as SuccessResult

        executed = []

        class TrackingOutputPlugin(OutputPlugin):
            def __init__(self, track_id: str, options, config_dir):
                super().__init__(options, config_dir)
                self._track_id = track_id

            def name(self) -> str:
                return f'tracking_{self._track_id}'

            def execute(self, df: FrameData) -> SuccessResult[None]:
                executed.append(self._track_id)
                return SuccessResult(None)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        plugins: list[OutputPlugin] = [
            TrackingOutputPlugin('first', {}, tmp_path),
            TrackingOutputPlugin('second', {}, tmp_path),
        ]
        data = Success(sample_lazyframe)
        result = execute_output(data, plugins)
        assert isinstance(result, Success)
        assert executed == ['first', 'second']

    def test_multiple_output_plugins_stops_on_failure(self, sample_lazyframe, tmp_path: Path) -> None:
        """Test that execution stops when a plugin fails."""
        from cryoflow_core.plugin import FrameData, OutputPlugin
        from returns.result import Failure as FailureResult, Success as SuccessResult

        executed = []

        class FailingOutputPlugin(OutputPlugin):
            def name(self) -> str:
                return 'failing_output'

            def execute(self, df: FrameData) -> FailureResult[Exception]:
                executed.append('failing')
                return FailureResult(ValueError('output failed'))

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        class AfterOutputPlugin(OutputPlugin):
            def name(self) -> str:
                return 'after_output'

            def execute(self, df: FrameData) -> SuccessResult[None]:
                executed.append('after')
                return SuccessResult(None)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        plugins = [
            FailingOutputPlugin({}, tmp_path),
            AfterOutputPlugin({}, tmp_path),
        ]
        data = Success(sample_lazyframe)
        result = execute_output(data, plugins)
        assert isinstance(result, Failure)
        assert executed == ['failing']


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
        from cryoflow_core.plugin import InputPlugin
        from returns.result import Failure as FailureResult

        class FailingInputPlugin(InputPlugin):
            def name(self) -> str:
                return 'failing_input'

            def execute(self) -> FailureResult[Exception]:
                return FailureResult(FileNotFoundError('file not found'))

            def dry_run(self):
                return FailureResult(FileNotFoundError('file not found'))

        input_plugin = FailingInputPlugin({}, tmp_path)
        output_plugin = DummyOutputPlugin({}, tmp_path)

        result = run_pipeline([input_plugin], [], [output_plugin])
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), FileNotFoundError)

    def test_pipeline_transform_fails(self, tmp_path: Path) -> None:
        """Test pipeline when transform plugin fails."""
        from cryoflow_core.plugin import FrameData, TransformPlugin
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


class TestLabelRouting:
    """Tests for label-based data routing in pipeline."""

    def test_execute_labeled_transform_chain_matching_label(self, sample_lazyframe, tmp_path: Path) -> None:
        """Transform plugin with matching label should process data."""
        plugin = DummyTransformPlugin({}, tmp_path, label='default')
        data_map: LabeledDataMap = {'default': Success(sample_lazyframe)}
        result_map = _execute_labeled_transform_chain(data_map, [plugin])
        assert 'default' in result_map
        assert isinstance(result_map['default'], Success)

    def test_execute_labeled_transform_chain_missing_label(self, sample_lazyframe, tmp_path: Path) -> None:
        """Transform plugin with non-existent label should create Failure entry."""
        plugin = DummyTransformPlugin({}, tmp_path, label='nonexistent')
        data_map: LabeledDataMap = {'default': Success(sample_lazyframe)}
        result_map = _execute_labeled_transform_chain(data_map, [plugin])
        assert 'nonexistent' in result_map
        assert isinstance(result_map['nonexistent'], Failure)

    def test_execute_labeled_output_matching_label(self, sample_lazyframe, tmp_path: Path) -> None:
        """Output plugin with matching label should succeed."""
        plugin = DummyOutputPlugin({}, tmp_path, label='default')
        data_map: LabeledDataMap = {'default': Success(sample_lazyframe)}
        result = _execute_labeled_output(data_map, [plugin])
        assert isinstance(result, Success)

    def test_execute_labeled_output_missing_label(self, sample_lazyframe, tmp_path: Path) -> None:
        """Output plugin with non-existent label should fail."""
        plugin = DummyOutputPlugin({}, tmp_path, label='nonexistent')
        data_map: LabeledDataMap = {'default': Success(sample_lazyframe)}
        result = _execute_labeled_output(data_map, [plugin])
        assert isinstance(result, Failure)
        assert 'nonexistent' in str(result.failure())

    def test_multiple_labels_routing(self, tmp_path: Path) -> None:
        """Test that multiple labeled data streams are processed independently."""
        input_a = DummyInputPlugin({}, tmp_path, label='stream_a')
        input_b = DummyInputPlugin({}, tmp_path, label='stream_b')
        output_a = DummyOutputPlugin({}, tmp_path, label='stream_a')
        output_b = DummyOutputPlugin({}, tmp_path, label='stream_b')

        result = run_pipeline([input_a, input_b], [], [output_a, output_b])
        assert isinstance(result, Success)


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

    def test_single_plugin_success(self, tmp_path: Path) -> None:
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
        result = execute_dry_run_chain(initial, [DummyTransformPlugin({}, tmp_path)])

        assert isinstance(result, Success)
        assert result.unwrap() == schema

    def test_plugin_validation_failure(self, tmp_path: Path) -> None:
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
        result = execute_dry_run_chain(initial, [FailingValidationPlugin({}, tmp_path)])

        assert isinstance(result, Failure)
        assert 'missing_col' in str(result.failure())

    def test_propagate_initial_failure(self, tmp_path: Path) -> None:
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
        result = execute_dry_run_chain(initial, [DummyPlugin({}, tmp_path)])

        assert isinstance(result, Failure)
        assert result.failure() == initial_error


class TestExecuteOutputDryRun:
    """Tests for output plugin dry-run execution."""

    def test_output_dry_run_success(self, tmp_path: Path) -> None:
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
        result = execute_output_dry_run(initial, [DummyOutputPlugin({}, tmp_path)])

        assert isinstance(result, Success)
        assert result.unwrap() == schema

    def test_output_dry_run_failure(self, tmp_path: Path) -> None:
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
        result = execute_output_dry_run(initial, [FailingOutputPlugin({}, tmp_path)])

        assert isinstance(result, Failure)
        assert 'Invalid output schema' in str(result.failure())

    def test_output_dry_run_propagate_failure(self, tmp_path: Path) -> None:
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
        result = execute_output_dry_run(initial, [DummyOutputPlugin({}, tmp_path)])

        assert isinstance(result, Failure)
        assert result.failure() == upstream_error


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
        from cryoflow_core.plugin import InputPlugin
        from returns.result import Failure as FailureResult

        class FailingInputPlugin(InputPlugin):
            def name(self) -> str:
                return 'failing_input'

            def execute(self):
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
        from cryoflow_core.plugin import TransformPlugin
        from returns.result import Failure as FailureResult

        class FailingTransformPlugin(TransformPlugin):
            def name(self) -> str:
                return 'failing_transform'

            def execute(self, df):
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
        from cryoflow_core.plugin import OutputPlugin
        from returns.result import Failure as FailureResult, Success as SuccessResult

        class FailingOutputPlugin(OutputPlugin):
            def name(self) -> str:
                return 'failing_output'

            def execute(self, df):
                return SuccessResult(None)

            def dry_run(self, schema: dict[str, pl.DataType]) -> FailureResult[Exception]:
                return FailureResult(ValueError('Invalid output format'))

        input_plugin = DummyInputPlugin({}, tmp_path)
        output_plugin = FailingOutputPlugin({}, tmp_path)

        result = run_dry_run_pipeline([input_plugin], [], [output_plugin])

        assert isinstance(result, Failure)
        assert 'Invalid output format' in str(result.failure())
