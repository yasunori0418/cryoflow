"""Tests for get_plugins function."""

import pluggy
import pytest

from cryoflow_core.hookspecs import CryoflowSpecs
from cryoflow_core.loader import _PluginHookRelay, get_plugins
from cryoflow_core.plugin import BasePlugin, InputPlugin, OutputPlugin, TransformPlugin

from ..conftest import DummyInputPlugin, DummyOutputPlugin, DummyTransformPlugin


class TestGetPlugins:
    def test_get_plugins_empty_input(self):
        pm = pluggy.PluginManager('cryoflow')
        pm.add_hookspecs(CryoflowSpecs)
        relay = _PluginHookRelay([], [], [])
        pm.register(relay)
        assert get_plugins(pm, InputPlugin) == []

    def test_get_plugins_empty_transform(self):
        pm = pluggy.PluginManager('cryoflow')
        pm.add_hookspecs(CryoflowSpecs)
        relay = _PluginHookRelay([], [], [])
        pm.register(relay)
        assert get_plugins(pm, TransformPlugin) == []

    def test_get_plugins_empty_output(self):
        pm = pluggy.PluginManager('cryoflow')
        pm.add_hookspecs(CryoflowSpecs)
        relay = _PluginHookRelay([], [], [])
        pm.register(relay)
        assert get_plugins(pm, OutputPlugin) == []

    def test_get_plugins_with_input(self, tmp_path):
        pm = pluggy.PluginManager('cryoflow')
        pm.add_hookspecs(CryoflowSpecs)
        i = DummyInputPlugin({}, tmp_path)
        relay = _PluginHookRelay([i], [], [])
        pm.register(relay)
        result = get_plugins(pm, InputPlugin)
        assert len(result) == 1
        assert result[0] is i

    def test_get_plugins_with_transform(self, tmp_path):
        pm = pluggy.PluginManager('cryoflow')
        pm.add_hookspecs(CryoflowSpecs)
        t = DummyTransformPlugin({}, tmp_path)
        relay = _PluginHookRelay([], [t], [])
        pm.register(relay)
        result = get_plugins(pm, TransformPlugin)
        assert len(result) == 1
        assert result[0] is t

    def test_get_plugins_with_output(self, tmp_path):
        pm = pluggy.PluginManager('cryoflow')
        pm.add_hookspecs(CryoflowSpecs)
        o = DummyOutputPlugin({}, tmp_path)
        relay = _PluginHookRelay([], [], [o])
        pm.register(relay)
        result = get_plugins(pm, OutputPlugin)
        assert len(result) == 1
        assert result[0] is o

    def test_get_plugins_unsupported_type(self):
        """Test that ValueError is raised for unsupported plugin types."""
        pm = pluggy.PluginManager('cryoflow')
        pm.add_hookspecs(CryoflowSpecs)
        relay = _PluginHookRelay([], [], [])
        pm.register(relay)

        # BasePlugin directly should raise an error
        with pytest.raises(ValueError, match='Unsupported plugin type'):
            get_plugins(pm, BasePlugin)
