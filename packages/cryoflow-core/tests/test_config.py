"""Tests for cryoflow_core.config module."""

from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from returns.result import Failure, Success

from cryoflow_core.config import (
    CryoflowConfig,
    PluginConfig,
    get_config_path,
    load_config,
)


# ---------------------------------------------------------------------------
# PluginConfig
# ---------------------------------------------------------------------------


class TestPluginConfig:
    def test_all_fields(self):
        pc = PluginConfig(
            name='my_plugin',
            module='my_mod',
            enabled=False,
            options={'k': 'v'},
        )
        assert pc.name == 'my_plugin'
        assert pc.module == 'my_mod'
        assert pc.enabled is False
        assert pc.options == {'k': 'v'}

    def test_defaults(self):
        pc = PluginConfig(name='p', module='m')
        assert pc.enabled is True
        assert pc.options == {}

    def test_missing_name(self):
        with pytest.raises(ValidationError):
            PluginConfig(module='m')  # type: ignore[call-arg]

    def test_missing_module(self):
        with pytest.raises(ValidationError):
            PluginConfig(name='p')  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# CryoflowConfig
# ---------------------------------------------------------------------------


class TestCryoflowConfig:
    def test_valid(self):
        cfg = CryoflowConfig(
            input_path=Path('/data/in.parquet'),
            plugins=[PluginConfig(name='p', module='m')],
        )
        assert isinstance(cfg.input_path, Path)
        assert len(cfg.plugins) == 1

    def test_missing_input_path(self):
        with pytest.raises(ValidationError):
            CryoflowConfig(
                plugins=[],
            )  # type: ignore[call-arg]

    def test_missing_plugins(self):
        with pytest.raises(ValidationError):
            CryoflowConfig(
                input_path='/data/in.parquet',
            )  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# get_config_path
# ---------------------------------------------------------------------------


class TestGetConfigPath:
    def test_returns_xdg_path(self):
        fake_home = Path('/tmp/fakexdg')
        with patch('cryoflow_core.config.xdg_config_home', return_value=fake_home):
            result = get_config_path(None)
        assert result == fake_home / 'cryoflow' / 'config.toml'

    def test_returns_target_config_path(self):
        fake_home = Path('/tmp/fakexdg')
        target_config_path = Path('/tmp/target/config.toml')
        with patch('cryoflow_core.config.xdg_config_home', return_value=fake_home):
            result = get_config_path(target_config_path)
        assert result == target_config_path


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_valid(self, valid_config_file):
        result = load_config(valid_config_file)
        assert isinstance(result, Success)
        cfg = result.unwrap()
        assert cfg.input_path == Path('/data/input.parquet')
        assert len(cfg.plugins) == 1
        assert cfg.plugins[0].name == 'my_plugin'
        assert cfg.plugins[0].options == {'threshold': 42}

    def test_minimal(self, minimal_config_file):
        result = load_config(minimal_config_file)
        assert isinstance(result, Success)
        cfg = result.unwrap()
        assert cfg.plugins == []

    def test_file_not_found(self, tmp_path):
        result = load_config(tmp_path / 'nonexistent.toml')
        assert isinstance(result, Failure)
        assert 'Config file not found' in str(result.failure())

    def test_invalid_toml_syntax(self, invalid_syntax_config_file):
        result = load_config(invalid_syntax_config_file)
        assert isinstance(result, Failure)
        assert 'Failed to parse TOML' in str(result.failure())

    def test_validation_error(self, missing_fields_config_file):
        result = load_config(missing_fields_config_file)
        assert isinstance(result, Failure)
        assert 'Config validation failed' in str(result.failure())

    def test_read_error(self, tmp_path):
        config_file = tmp_path / 'unreadable.toml'
        config_file.write_text('dummy')
        config_file.chmod(0o000)
        result = load_config(config_file)
        assert isinstance(result, Failure)
        assert 'Failed to read config file' in str(result.failure())
        config_file.chmod(0o644)  # restore for cleanup

    def test_multi_plugin(self, multi_plugin_config_file):
        result = load_config(multi_plugin_config_file)
        assert isinstance(result, Success)
        cfg = result.unwrap()
        assert len(cfg.plugins) == 3
        assert cfg.plugins[0].name == 'plugin_a'
        assert cfg.plugins[0].enabled is True
        assert cfg.plugins[1].name == 'plugin_b'
        assert cfg.plugins[1].enabled is False
        assert cfg.plugins[2].name == 'plugin_c'
        assert cfg.plugins[2].options == {'key': 'value'}

    def test_input_path_relative_to_config(self, tmp_path):
        """Test that relative input_path is resolved relative to config directory."""
        config_dir = tmp_path / 'config_dir'
        config_dir.mkdir()
        config_file = config_dir / 'config.toml'
        config_file.write_text("""\
input_path = "data/input.parquet"
plugins = []
""")
        result = load_config(config_file)
        assert isinstance(result, Success)
        cfg = result.unwrap()
        expected_path = (config_dir / 'data' / 'input.parquet').resolve()
        assert cfg.input_path == expected_path

    def test_input_path_absolute_unchanged(self, tmp_path):
        """Test that absolute input_path is preserved as-is (after normalization)."""
        config_file = tmp_path / 'config.toml'
        absolute_path = '/absolute/path/to/data.parquet'
        config_file.write_text(f"""\
input_path = "{absolute_path}"
plugins = []
""")
        result = load_config(config_file)
        assert isinstance(result, Success)
        cfg = result.unwrap()
        # Absolute paths are normalized with resolve()
        assert cfg.input_path == Path(absolute_path).resolve()
