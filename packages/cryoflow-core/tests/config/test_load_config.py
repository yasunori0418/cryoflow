"""Tests for load_config function."""

from returns.result import Failure, Success

from cryoflow_core.config import load_config


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
