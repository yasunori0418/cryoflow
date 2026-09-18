"""Tests for _resolve_module_path function."""

from pathlib import Path

from returns.result import Failure

from cryoflow_core.loader import PluginLoadError, _resolve_module_path


class TestResolveModulePath:
    def test_relative_path(self, tmp_path: Path):
        plugin_file = tmp_path / 'plugins' / 'my_plugin.py'
        plugin_file.parent.mkdir(parents=True)
        plugin_file.write_text('# plugin')
        result = _resolve_module_path('plugins/my_plugin.py', tmp_path)
        assert result.unwrap() == plugin_file.resolve()

    def test_absolute_path(self, tmp_path: Path):
        plugin_file = tmp_path / 'my_plugin.py'
        plugin_file.write_text('# plugin')
        result = _resolve_module_path(str(plugin_file), tmp_path)
        assert result.unwrap() == plugin_file.resolve()

    def test_nonexistent_path_returns_failure(self, tmp_path: Path):
        result = _resolve_module_path('nonexistent.py', tmp_path)
        assert isinstance(result, Failure)
        error = result.failure()
        assert isinstance(error, PluginLoadError)
        assert 'does not exist' in str(error)
