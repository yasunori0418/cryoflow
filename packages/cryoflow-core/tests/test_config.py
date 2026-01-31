"""Tests for cryoflow_core.config module."""

from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from cryoflow_core.config import (
    ConfigLoadError,
    CryoflowConfig,
    PluginConfig,
    get_default_config_path,
    load_config,
)


# ---------------------------------------------------------------------------
# PluginConfig
# ---------------------------------------------------------------------------


class TestPluginConfig:
    def test_all_fields(self):
        pc = PluginConfig(
            name="my_plugin",
            module="my_mod",
            enabled=False,
            options={"k": "v"},
        )
        assert pc.name == "my_plugin"
        assert pc.module == "my_mod"
        assert pc.enabled is False
        assert pc.options == {"k": "v"}

    def test_defaults(self):
        pc = PluginConfig(name="p", module="m")
        assert pc.enabled is True
        assert pc.options == {}

    def test_missing_name(self):
        with pytest.raises(ValidationError):
            PluginConfig(module="m")  # type: ignore[call-arg]

    def test_missing_module(self):
        with pytest.raises(ValidationError):
            PluginConfig(name="p")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# CryoflowConfig
# ---------------------------------------------------------------------------


class TestCryoflowConfig:
    def test_valid(self):
        cfg = CryoflowConfig(
            input_path="/data/in.parquet",
            output_target="/data/out.parquet",
            plugins=[PluginConfig(name="p", module="m")],
        )
        assert isinstance(cfg.input_path, Path)
        assert cfg.output_target == "/data/out.parquet"
        assert len(cfg.plugins) == 1

    def test_missing_input_path(self):
        with pytest.raises(ValidationError):
            CryoflowConfig(
                output_target="/data/out.parquet",
                plugins=[],
            )  # type: ignore[call-arg]

    def test_missing_output_target(self):
        with pytest.raises(ValidationError):
            CryoflowConfig(
                input_path="/data/in.parquet",
                plugins=[],
            )  # type: ignore[call-arg]

    def test_missing_plugins(self):
        with pytest.raises(ValidationError):
            CryoflowConfig(
                input_path="/data/in.parquet",
                output_target="/data/out.parquet",
            )  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# get_default_config_path
# ---------------------------------------------------------------------------


class TestGetDefaultConfigPath:
    def test_returns_xdg_path(self):
        fake_home = Path("/tmp/fakexdg")
        with patch("cryoflow_core.config.xdg_config_home", return_value=fake_home):
            result = get_default_config_path()
        assert result == fake_home / "cryoflow" / "config.toml"


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_valid(self, valid_config_file):
        cfg = load_config(valid_config_file)
        assert isinstance(cfg, CryoflowConfig)
        assert cfg.input_path == Path("/data/input.parquet")
        assert cfg.output_target == "/data/output.parquet"
        assert len(cfg.plugins) == 1
        assert cfg.plugins[0].name == "my_plugin"
        assert cfg.plugins[0].options == {"threshold": 42}

    def test_minimal(self, minimal_config_file):
        cfg = load_config(minimal_config_file)
        assert cfg.plugins == []

    def test_file_not_found(self, tmp_path):
        with pytest.raises(ConfigLoadError, match="Config file not found"):
            load_config(tmp_path / "nonexistent.toml")

    def test_invalid_toml_syntax(self, invalid_syntax_config_file):
        with pytest.raises(ConfigLoadError, match="Failed to parse TOML"):
            load_config(invalid_syntax_config_file)

    def test_validation_error(self, missing_fields_config_file):
        with pytest.raises(ConfigLoadError, match="Config validation failed"):
            load_config(missing_fields_config_file)

    def test_read_error(self, tmp_path):
        config_file = tmp_path / "unreadable.toml"
        config_file.write_text("dummy")
        config_file.chmod(0o000)
        with pytest.raises(ConfigLoadError, match="Failed to read config file"):
            load_config(config_file)
        config_file.chmod(0o644)  # restore for cleanup

    def test_multi_plugin(self, multi_plugin_config_file):
        cfg = load_config(multi_plugin_config_file)
        assert len(cfg.plugins) == 3
        assert cfg.plugins[0].name == "plugin_a"
        assert cfg.plugins[0].enabled is True
        assert cfg.plugins[1].name == "plugin_b"
        assert cfg.plugins[1].enabled is False
        assert cfg.plugins[2].name == "plugin_c"
        assert cfg.plugins[2].options == {"key": "value"}
