"""Tests for _load_module_from_path function."""

import sys
from unittest.mock import patch
from pathlib import Path

import pytest

from cryoflow_core.loader import PluginLoadError, _load_module_from_path

from .conftest import SYNTAX_ERROR_SOURCE


class TestLoadModuleFromPath:
    def test_loads_module(self, plugin_py_file: Path):
        module = _load_module_from_path('test_plugin', plugin_py_file)
        assert hasattr(module, 'MyTransformPlugin')
        assert 'cryoflow_plugin_test_plugin' in sys.modules

    def test_syntax_error_raises(self, tmp_path: Path):
        bad_file = tmp_path / 'bad.py'
        bad_file.write_text(SYNTAX_ERROR_SOURCE)
        with pytest.raises(PluginLoadError, match='failed to execute module'):
            _load_module_from_path('bad_plugin', bad_file)

    def test_spec_none_raises(self, plugin_py_file: Path):
        with patch(
            'cryoflow_core.loader.importlib.util.spec_from_file_location',
            return_value=None,
        ):
            with pytest.raises(PluginLoadError, match='failed to create module spec'):
                _load_module_from_path('spec_none', plugin_py_file)

    def test_syntax_error_cleans_sys_modules(self, tmp_path: Path):
        bad_file = tmp_path / 'bad.py'
        bad_file.write_text(SYNTAX_ERROR_SOURCE)
        try:
            _load_module_from_path('bad_cleanup', bad_file)
        except PluginLoadError:
            pass
        assert 'cryoflow_plugin_bad_cleanup' not in sys.modules
