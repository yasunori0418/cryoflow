"""Tests for _load_module_from_dotpath function."""

from returns.result import Failure

from cryoflow_core.loader import PluginLoadError, _load_module_from_dotpath


class TestLoadModuleFromDotpath:
    def test_loads_real_module(self):
        result = _load_module_from_dotpath('cfg', 'cryoflow_core.config')
        assert hasattr(result.unwrap(), 'CryoflowConfig')

    def test_nonexistent_module_returns_failure(self):
        result = _load_module_from_dotpath('nope', 'nonexistent.module.path')
        assert isinstance(result, Failure)
        error = result.failure()
        assert isinstance(error, PluginLoadError)
        assert 'not found' in str(error)
