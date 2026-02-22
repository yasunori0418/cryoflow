"""Tests for plugin path resolution."""

from pathlib import Path

from ..conftest import DummyInputPlugin, DummyTransformPlugin


class TestPathResolution:
    def test_resolve_path_relative(self, tmp_path: Path):
        """Test that relative paths are resolved relative to config_dir."""
        config_dir = tmp_path / 'config'
        config_dir.mkdir()
        p = DummyTransformPlugin({}, config_dir)
        result = p.resolve_path('data/output.parquet')
        expected = (config_dir / 'data' / 'output.parquet').resolve()
        assert result == expected

    def test_resolve_path_absolute(self, tmp_path: Path):
        """Test that absolute paths are preserved (after normalization)."""
        config_dir = tmp_path / 'config'
        config_dir.mkdir()
        p = DummyTransformPlugin({}, config_dir)
        absolute_path = Path('/absolute/path/to/file.parquet')
        result = p.resolve_path(absolute_path)
        assert result == absolute_path.resolve()

    def test_resolve_path_string_input(self, tmp_path: Path):
        """Test that string paths work correctly."""
        config_dir = tmp_path / 'config'
        config_dir.mkdir()
        p = DummyTransformPlugin({}, config_dir)
        result = p.resolve_path('relative/path.txt')
        expected = (config_dir / 'relative' / 'path.txt').resolve()
        assert result == expected

    def test_resolve_path_path_input(self, tmp_path: Path):
        """Test that Path objects work correctly."""
        config_dir = tmp_path / 'config'
        config_dir.mkdir()
        p = DummyTransformPlugin({}, config_dir)
        result = p.resolve_path(Path('relative/path.txt'))
        expected = (config_dir / 'relative' / 'path.txt').resolve()
        assert result == expected

    def test_input_plugin_resolve_path(self, tmp_path: Path):
        """Test that InputPlugin can also resolve paths."""
        p = DummyInputPlugin({}, tmp_path)
        result = p.resolve_path('data/file.parquet')
        expected = (tmp_path / 'data' / 'file.parquet').resolve()
        assert result == expected
