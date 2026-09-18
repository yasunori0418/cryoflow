"""Tests for _discover_plugin_classes function."""

import types

from returns.result import Failure

from cryoflow_core.loader import PluginLoadError, _discover_plugin_classes
from cryoflow_core.plugin import BasePlugin, InputPlugin, TransformPlugin

from ..conftest import DummyInputPlugin, DummyOutputPlugin, DummyTransformPlugin


class TestDiscoverPluginClasses:
    def test_discovers_concrete_classes(self):
        mod = types.ModuleType('fake_mod')
        mod.DummyInputPlugin = DummyInputPlugin  # pyright: ignore[reportAttributeAccessIssue]
        mod.DummyTransformPlugin = DummyTransformPlugin  # pyright: ignore[reportAttributeAccessIssue]
        mod.DummyOutputPlugin = DummyOutputPlugin  # pyright: ignore[reportAttributeAccessIssue]
        classes = _discover_plugin_classes('test', mod).unwrap()
        assert DummyInputPlugin in classes
        assert DummyTransformPlugin in classes
        assert DummyOutputPlugin in classes

    def test_excludes_abstract_classes(self):
        mod = types.ModuleType('fake_mod')
        mod.TransformPlugin = TransformPlugin  # pyright: ignore[reportAttributeAccessIssue]
        mod.InputPlugin = InputPlugin  # pyright: ignore[reportAttributeAccessIssue]
        mod.DummyTransformPlugin = DummyTransformPlugin  # pyright: ignore[reportAttributeAccessIssue]
        classes = _discover_plugin_classes('test', mod).unwrap()
        assert TransformPlugin not in classes
        assert InputPlugin not in classes
        assert DummyTransformPlugin in classes

    def test_excludes_base_classes(self):
        mod = types.ModuleType('fake_mod')
        mod.BasePlugin = BasePlugin  # pyright: ignore[reportAttributeAccessIssue]
        mod.DummyTransformPlugin = DummyTransformPlugin  # pyright: ignore[reportAttributeAccessIssue]
        classes = _discover_plugin_classes('test', mod).unwrap()
        assert BasePlugin not in classes

    def test_empty_module_returns_failure(self):
        mod = types.ModuleType('empty_mod')
        result = _discover_plugin_classes('empty', mod)
        assert isinstance(result, Failure)
        error = result.failure()
        assert isinstance(error, PluginLoadError)
        assert 'no BasePlugin subclasses' in str(error)
