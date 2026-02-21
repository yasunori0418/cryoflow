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
            label='sales',
            options={'k': 'v'},
        )
        assert pc.name == 'my_plugin'
        assert pc.module == 'my_mod'
        assert pc.enabled is False
        assert pc.label == 'sales'
        assert pc.options == {'k': 'v'}

    def test_defaults(self):
        pc = PluginConfig(name='p', module='m')
        assert pc.enabled is True
        assert pc.label == 'default'
        assert pc.options == {}

    def test_label_default(self):
        pc = PluginConfig(name='p', module='m')
        assert pc.label == 'default'

    def test_label_custom(self):
        pc = PluginConfig(name='p', module='m', label='custom_stream')
        assert pc.label == 'custom_stream'

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
            input_plugins=[PluginConfig(name='p', module='m')],
            transform_plugins=[PluginConfig(name='p2', module='m2')],
            output_plugins=[],
        )
        assert len(cfg.input_plugins) == 1
        assert len(cfg.transform_plugins) == 1
        assert len(cfg.output_plugins) == 0

    def test_missing_input_plugins(self):
        with pytest.raises(ValidationError):
            CryoflowConfig(
                transform_plugins=[],
                output_plugins=[],
            )  # type: ignore[call-arg]

    def test_missing_transform_plugins(self):
        with pytest.raises(ValidationError):
            CryoflowConfig(
                input_plugins=[],
                output_plugins=[],
            )  # type: ignore[call-arg]

    def test_missing_output_plugins(self):
        with pytest.raises(ValidationError):
            CryoflowConfig(
                input_plugins=[],
                transform_plugins=[],
            )  # type: ignore[call-arg]

    def test_empty_input_plugins(self):
        cfg = CryoflowConfig(
            input_plugins=[],
            transform_plugins=[],
            output_plugins=[],
        )
        assert cfg.input_plugins == []


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
        assert len(cfg.input_plugins) == 1
        assert cfg.input_plugins[0].name == 'my_input'
        assert len(cfg.transform_plugins) == 1
        assert cfg.transform_plugins[0].name == 'my_plugin'
        assert cfg.transform_plugins[0].options == {'threshold': 42}
        assert cfg.output_plugins == []

    def test_minimal(self, minimal_config_file):
        result = load_config(minimal_config_file)
        assert isinstance(result, Success)
        cfg = result.unwrap()
        assert cfg.input_plugins == []
        assert cfg.transform_plugins == []
        assert cfg.output_plugins == []

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
        assert len(cfg.input_plugins) == 1
        assert cfg.input_plugins[0].name == 'input_a'
        assert cfg.input_plugins[0].label == 'sales'
        assert len(cfg.transform_plugins) == 2
        assert cfg.transform_plugins[0].name == 'plugin_a'
        assert cfg.transform_plugins[0].enabled is True
        assert cfg.transform_plugins[1].name == 'plugin_b'
        assert cfg.transform_plugins[1].enabled is False
        assert len(cfg.output_plugins) == 1
        assert cfg.output_plugins[0].name == 'plugin_c'
        assert cfg.output_plugins[0].options == {'key': 'value'}

    def test_label_default_value(self, tmp_path):
        """Test that label defaults to 'default' when not specified."""
        config_file = tmp_path / 'config.toml'
        config_file.write_text("""\
transform_plugins = []
output_plugins = []

[[input_plugins]]
name = "my_input"
module = "my_mod"
""")
        result = load_config(config_file)
        assert isinstance(result, Success)
        cfg = result.unwrap()
        assert cfg.input_plugins[0].label == 'default'

    def test_label_custom_value(self, tmp_path):
        """Test that label is correctly parsed from TOML."""
        config_file = tmp_path / 'config.toml'
        config_file.write_text("""\
transform_plugins = []
output_plugins = []

[[input_plugins]]
name = "my_input"
module = "my_mod"
label = "sales_data"
""")
        result = load_config(config_file)
        assert isinstance(result, Success)
        cfg = result.unwrap()
        assert cfg.input_plugins[0].label == 'sales_data'
