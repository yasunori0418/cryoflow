"""Tests for _instantiate_plugins function."""

from pathlib import Path

from returns.result import Failure

from cryoflow_core.loader import PluginLoadError, _instantiate_plugins

from ..conftest import BrokenInitPlugin, DummyOutputPlugin, DummyTransformPlugin


class TestInstantiatePlugins:
    def test_normal_instantiation(self, tmp_path: Path):
        opts = {'key': 'value'}
        instances = _instantiate_plugins('test', [DummyTransformPlugin, DummyOutputPlugin], opts, tmp_path).unwrap()
        assert len(instances) == 2
        assert all(inst.options is opts for inst in instances)

    def test_options_propagation(self, tmp_path: Path):
        opts = {'threshold': 42}
        instances = _instantiate_plugins('test', [DummyTransformPlugin], opts, tmp_path).unwrap()
        assert instances[0].options == {'threshold': 42}

    def test_label_propagation(self, tmp_path: Path):
        """Test that label is correctly passed to plugin instances."""
        opts = {}
        instances = _instantiate_plugins('test', [DummyTransformPlugin], opts, tmp_path, label='sales').unwrap()
        assert instances[0].label == 'sales'

    def test_default_label(self, tmp_path: Path):
        """Test that default label is 'default'."""
        opts = {}
        instances = _instantiate_plugins('test', [DummyTransformPlugin], opts, tmp_path).unwrap()
        assert instances[0].label == 'default'

    def test_broken_init_returns_failure(self, tmp_path: Path):
        result = _instantiate_plugins('test', [BrokenInitPlugin], {}, tmp_path)
        assert isinstance(result, Failure)
        error = result.failure()
        assert isinstance(error, PluginLoadError)
        assert 'failed to instantiate' in str(error)
