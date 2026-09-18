"""Tests for _load_module_from_path function."""

import sys
from pathlib import Path
from unittest.mock import patch

from returns.result import Failure

from cryoflow_core.loader import PluginLoadError, _load_module_from_path

from .conftest import SYNTAX_ERROR_SOURCE


class TestLoadModuleFromPath:
    def test_loads_module(self, plugin_py_file: Path):
        result = _load_module_from_path('test_plugin', plugin_py_file)
        assert hasattr(result.unwrap(), 'MyTransformPlugin')
        assert 'cryoflow_plugin_test_plugin' in sys.modules

    def test_syntax_error_returns_failure(self, tmp_path: Path):
        bad_file = tmp_path / 'bad.py'
        bad_file.write_text(SYNTAX_ERROR_SOURCE)
        result = _load_module_from_path('bad_plugin', bad_file)
        assert isinstance(result, Failure)
        error = result.failure()
        assert isinstance(error, PluginLoadError)
        assert 'failed to execute module' in str(error)

    def test_spec_none_returns_failure(self, plugin_py_file: Path):
        with patch(
            'cryoflow_core.loader.importlib.util.spec_from_file_location',
            return_value=None,
        ):
            result = _load_module_from_path('spec_none', plugin_py_file)
        assert isinstance(result, Failure)
        error = result.failure()
        assert isinstance(error, PluginLoadError)
        assert 'failed to create module spec' in str(error)

    def test_syntax_error_cleans_sys_modules(self, tmp_path: Path):
        bad_file = tmp_path / 'bad.py'
        bad_file.write_text(SYNTAX_ERROR_SOURCE)
        _load_module_from_path('bad_cleanup', bad_file)
        assert 'cryoflow_plugin_bad_cleanup' not in sys.modules
