"""Tests for _load_module_from_dotpath function."""

import pytest

from cryoflow_core.loader import PluginLoadError, _load_module_from_dotpath


class TestLoadModuleFromDotpath:
    def test_loads_real_module(self):
        module = _load_module_from_dotpath('cfg', 'cryoflow_core.config')
        assert hasattr(module, 'CryoflowConfig')

    def test_nonexistent_module_raises(self):
        with pytest.raises(PluginLoadError, match='not found'):
            _load_module_from_dotpath('nope', 'nonexistent.module.path')
