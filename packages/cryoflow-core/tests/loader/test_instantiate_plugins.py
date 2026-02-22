"""Tests for _instantiate_plugins function."""

from pathlib import Path

import pytest

from cryoflow_core.loader import PluginLoadError, _instantiate_plugins

from ..conftest import BrokenInitPlugin, DummyOutputPlugin, DummyTransformPlugin


class TestInstantiatePlugins:
    def test_normal_instantiation(self, tmp_path: Path):
        opts = {'key': 'value'}
        instances = _instantiate_plugins('test', [DummyTransformPlugin, DummyOutputPlugin], opts, tmp_path)
        assert len(instances) == 2
        assert all(inst.options is opts for inst in instances)

    def test_options_propagation(self, tmp_path: Path):
        opts = {'threshold': 42}
        instances = _instantiate_plugins('test', [DummyTransformPlugin], opts, tmp_path)
        assert instances[0].options == {'threshold': 42}

    def test_label_propagation(self, tmp_path: Path):
        """Test that label is correctly passed to plugin instances."""
        opts = {}
        instances = _instantiate_plugins('test', [DummyTransformPlugin], opts, tmp_path, label='sales')
        assert instances[0].label == 'sales'

    def test_default_label(self, tmp_path: Path):
        """Test that default label is 'default'."""
        opts = {}
        instances = _instantiate_plugins('test', [DummyTransformPlugin], opts, tmp_path)
        assert instances[0].label == 'default'

    def test_broken_init_raises(self, tmp_path: Path):
        with pytest.raises(PluginLoadError, match='failed to instantiate'):
            _instantiate_plugins('test', [BrokenInitPlugin], {}, tmp_path)
