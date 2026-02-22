"""Tests for label-based data routing in pipeline."""

from pathlib import Path

from returns.result import Failure, Success

from cryoflow_core.pipeline import LabeledDataMap, _execute_labeled_output, _execute_labeled_transform_chain, run_pipeline

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
