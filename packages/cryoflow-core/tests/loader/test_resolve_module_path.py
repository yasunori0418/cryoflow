"""Tests for _resolve_module_path function."""

import pytest

from cryoflow_core.loader import PluginLoadError, _resolve_module_path


class TestResolveModulePath:
    def test_relative_path(self, tmp_path):
        plugin_file = tmp_path / 'plugins' / 'my_plugin.py'
        plugin_file.parent.mkdir(parents=True)
        plugin_file.write_text('# plugin')
        result = _resolve_module_path('plugins/my_plugin.py', tmp_path)
        assert result == plugin_file.resolve()

    def test_absolute_path(self, tmp_path):
        plugin_file = tmp_path / 'my_plugin.py'
        plugin_file.write_text('# plugin')
        result = _resolve_module_path(str(plugin_file), tmp_path)
        assert result == plugin_file.resolve()

    def test_nonexistent_path_raises(self, tmp_path):
        with pytest.raises(PluginLoadError, match='does not exist'):
            _resolve_module_path('nonexistent.py', tmp_path)
