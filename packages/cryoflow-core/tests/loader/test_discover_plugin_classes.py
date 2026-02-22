"""Tests for _discover_plugin_classes function."""

import types

import pytest

from cryoflow_core.loader import PluginLoadError, _discover_plugin_classes
from cryoflow_core.plugin import BasePlugin, InputPlugin, TransformPlugin

from ..conftest import DummyInputPlugin, DummyOutputPlugin, DummyTransformPlugin


class TestDiscoverPluginClasses:
    def test_discovers_concrete_classes(self):
        mod = types.ModuleType('fake_mod')
        setattr(mod, 'DummyInputPlugin', DummyInputPlugin)  # pyright: ignore[reportAttributeAccessIssue]
        setattr(mod, 'DummyTransformPlugin', DummyTransformPlugin)  # pyright: ignore[reportAttributeAccessIssue]
        setattr(mod, 'DummyOutputPlugin', DummyOutputPlugin)  # pyright: ignore[reportAttributeAccessIssue]
        classes = _discover_plugin_classes('test', mod)
        assert DummyInputPlugin in classes
        assert DummyTransformPlugin in classes
        assert DummyOutputPlugin in classes

    def test_excludes_abstract_classes(self):
        mod = types.ModuleType('fake_mod')
        setattr(mod, 'TransformPlugin', TransformPlugin)  # pyright: ignore[reportAttributeAccessIssue]
        setattr(mod, 'InputPlugin', InputPlugin)  # pyright: ignore[reportAttributeAccessIssue]
        setattr(mod, 'DummyTransformPlugin', DummyTransformPlugin)  # pyright: ignore[reportAttributeAccessIssue]
        classes = _discover_plugin_classes('test', mod)
        assert TransformPlugin not in classes
        assert InputPlugin not in classes
        assert DummyTransformPlugin in classes

    def test_excludes_base_classes(self):
        mod = types.ModuleType('fake_mod')
        setattr(mod, 'BasePlugin', BasePlugin)  # pyright: ignore[reportAttributeAccessIssue]
        setattr(mod, 'DummyTransformPlugin', DummyTransformPlugin)  # pyright: ignore[reportAttributeAccessIssue]
        classes = _discover_plugin_classes('test', mod)
        assert BasePlugin not in classes

    def test_empty_module_raises(self):
        mod = types.ModuleType('empty_mod')
        with pytest.raises(PluginLoadError, match='no BasePlugin subclasses'):
            _discover_plugin_classes('empty', mod)
