"""Tests for label-based data routing in pipeline."""

from pathlib import Path

import polars as pl
from returns.result import Failure, Success

from cryoflow_core.pipeline import (
    LabeledDataMap,
    LabeledSchemaMap,
    _execute_labeled_dry_run_transform_chain,
    _execute_labeled_output,
    _execute_labeled_output_dry_run,
    _execute_labeled_transform_chain,
    run_pipeline,
)
from cryoflow_core.plugin import FrameData, TransformPlugin

from ..conftest import DummyInputPlugin, DummyOutputPlugin, DummyTransformPlugin


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


class TestDryRunLabelRouting:
    """Tests for label-based schema routing in the dry-run pipeline."""

    def test_dry_run_transform_chain_matching_label(self, tmp_path: Path) -> None:
        """Transform plugin with matching label should validate that schema."""
        plugin = DummyTransformPlugin({}, tmp_path, label='sales')
        schema_map: LabeledSchemaMap = {'sales': Success({'a': pl.Int64()})}
        result_map = _execute_labeled_dry_run_transform_chain(schema_map, [plugin])
        assert isinstance(result_map['sales'], Success)
        assert result_map['sales'].unwrap() == {'a': pl.Int64()}

    def test_dry_run_transform_chain_missing_label(self, tmp_path: Path) -> None:
        """Transform plugin with non-existent label should create Failure entry."""
        plugin = DummyTransformPlugin({}, tmp_path, label='nonexistent')
        schema_map: LabeledSchemaMap = {'default': Success({'a': pl.Int64()})}
        result_map = _execute_labeled_dry_run_transform_chain(schema_map, [plugin])
        assert isinstance(result_map['nonexistent'], Failure)
        assert isinstance(result_map['nonexistent'].failure(), KeyError)

    def test_dry_run_output_matching_label(self, tmp_path: Path) -> None:
        """Output plugin with matching label should return that label's schema."""
        plugin = DummyOutputPlugin({}, tmp_path, label='sales')
        schema_map: LabeledSchemaMap = {
            'default': Success({'a': pl.Int64()}),
            'sales': Success({'b': pl.String()}),
        }
        result = _execute_labeled_output_dry_run(schema_map, [plugin])
        assert isinstance(result, Success)
        assert result.unwrap() == {'b': pl.String()}

    def test_dry_run_output_missing_label(self, tmp_path: Path) -> None:
        """Output plugin with non-existent label should fail immediately."""
        plugin = DummyOutputPlugin({}, tmp_path, label='nonexistent')
        schema_map: LabeledSchemaMap = {'default': Success({'a': pl.Int64()})}
        result = _execute_labeled_output_dry_run(schema_map, [plugin])
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), KeyError)
        assert 'nonexistent' in str(result.failure())

    def test_dry_run_output_without_plugins_returns_default(self) -> None:
        """No output plugin should fall back to the 'default' label schema."""
        schema_map: LabeledSchemaMap = {'default': Success({'a': pl.Int64()})}
        result = _execute_labeled_output_dry_run(schema_map, [])
        assert isinstance(result, Success)
        assert result.unwrap() == {'a': pl.Int64()}

    def test_dry_run_output_without_plugins_and_no_default(self) -> None:
        """No output plugin and no 'default' label should fail."""
        schema_map: LabeledSchemaMap = {'sales': Success({'a': pl.Int64()})}
        result = _execute_labeled_output_dry_run(schema_map, [])
        assert isinstance(result, Failure)
        assert isinstance(result.failure(), KeyError)

    def test_dry_run_transform_chain_accumulates_within_label(self, tmp_path: Path) -> None:
        """Two transform plugins on the same label should chain their schemas."""

        class AddColumnPlugin(TransformPlugin):
            def name(self) -> str:
                return 'add_column'

            def execute(self, df: FrameData) -> Success[FrameData]:
                return Success(df)

            def dry_run(self, schema: dict[str, pl.DataType]) -> Success[dict[str, pl.DataType]]:
                return Success({**schema, f'added_{len(schema)}': pl.Int64()})

        first = AddColumnPlugin({}, tmp_path, label='sales')
        second = AddColumnPlugin({}, tmp_path, label='sales')
        schema_map: LabeledSchemaMap = {'sales': Success({'a': pl.Int64()})}
        result_map = _execute_labeled_dry_run_transform_chain(schema_map, [first, second])
        assert isinstance(result_map['sales'], Success)
        assert result_map['sales'].unwrap() == {'a': pl.Int64(), 'added_1': pl.Int64(), 'added_2': pl.Int64()}

    def test_dry_run_output_returns_last_plugin_label_schema(self, tmp_path: Path) -> None:
        """With several output plugins the last one's label schema should be returned."""
        sales_output = DummyOutputPlugin({}, tmp_path, label='sales')
        stock_output = DummyOutputPlugin({}, tmp_path, label='stock')
        schema_map: LabeledSchemaMap = {
            'sales': Success({'amount': pl.Int64()}),
            'stock': Success({'quantity': pl.Int64()}),
        }
        result = _execute_labeled_output_dry_run(schema_map, [sales_output, stock_output])
        assert isinstance(result, Success)
        assert result.unwrap() == {'quantity': pl.Int64()}

    def test_dry_run_output_without_default_label(self, tmp_path: Path) -> None:
        """Output plugin on a non-default label should succeed without a 'default' entry."""
        plugin = DummyOutputPlugin({}, tmp_path, label='sales')
        schema_map: LabeledSchemaMap = {'sales': Success({'amount': pl.Int64()})}
        result = _execute_labeled_output_dry_run(schema_map, [plugin])
        assert isinstance(result, Success)
        assert result.unwrap() == {'amount': pl.Int64()}
