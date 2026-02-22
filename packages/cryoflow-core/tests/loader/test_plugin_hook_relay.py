"""Tests for _PluginHookRelay class."""

from pathlib import Path

from cryoflow_core.loader import _PluginHookRelay

from ..conftest import DummyInputPlugin, DummyOutputPlugin, DummyTransformPlugin


class TestPluginHookRelay:
    def test_register_input_plugins(self, tmp_path: Path):
        i = DummyInputPlugin({}, tmp_path)
        relay = _PluginHookRelay([i], [], [])
        assert relay.register_input_plugins() == [i]

    def test_register_transform_plugins(self, tmp_path: Path):
        t = DummyTransformPlugin({}, tmp_path)
        relay = _PluginHookRelay([], [t], [])
        assert relay.register_transform_plugins() == [t]

    def test_register_output_plugins(self, tmp_path: Path):
        o = DummyOutputPlugin({}, tmp_path)
        relay = _PluginHookRelay([], [], [o])
        assert relay.register_output_plugins() == [o]

    def test_empty_lists(self):
        relay = _PluginHookRelay([], [], [])
        assert relay.register_input_plugins() == []
        assert relay.register_transform_plugins() == []
        assert relay.register_output_plugins() == []
