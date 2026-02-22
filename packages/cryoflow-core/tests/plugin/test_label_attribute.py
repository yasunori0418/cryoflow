"""Tests for plugin label attribute."""

from ..conftest import DummyInputPlugin, DummyOutputPlugin, DummyTransformPlugin
from cryoflow_core.plugin import DEFAULT_LABEL


class TestLabelAttribute:
    def test_default_label(self, tmp_path):
        p = DummyTransformPlugin({}, tmp_path)
        assert p.label == DEFAULT_LABEL
        assert p.label == 'default'

    def test_custom_label(self, tmp_path):
        p = DummyTransformPlugin({}, tmp_path, label='sales')
        assert p.label == 'sales'

    def test_input_plugin_default_label(self, tmp_path):
        p = DummyInputPlugin({}, tmp_path)
        assert p.label == 'default'

    def test_input_plugin_custom_label(self, tmp_path):
        p = DummyInputPlugin({}, tmp_path, label='orders')
        assert p.label == 'orders'

    def test_output_plugin_label(self, tmp_path):
        p = DummyOutputPlugin({}, tmp_path, label='results')
        assert p.label == 'results'
