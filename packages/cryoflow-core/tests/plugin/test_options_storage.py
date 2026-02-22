"""Tests for plugin options storage."""

from ..conftest import DummyInputPlugin, DummyOutputPlugin, DummyTransformPlugin


class TestOptionsStorage:
    def test_input_plugin_stores_options(self, tmp_path):
        opts = {'input_path': 'data.parquet'}
        p = DummyInputPlugin(opts, tmp_path)
        assert p.options is opts

    def test_transform_plugin_stores_options(self, tmp_path):
        opts = {'threshold': 10}
        p = DummyTransformPlugin(opts, tmp_path)
        assert p.options is opts

    def test_output_plugin_stores_options(self, tmp_path):
        opts = {'format': 'csv'}
        p = DummyOutputPlugin(opts, tmp_path)
        assert p.options is opts

    def test_empty_options(self, tmp_path):
        p = DummyTransformPlugin({}, tmp_path)
        assert p.options == {}
