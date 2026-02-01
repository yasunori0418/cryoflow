"""Tests for cryoflow_core.cli module."""

from pathlib import Path
from unittest.mock import patch

import pluggy
from typer.testing import CliRunner

from cryoflow_core.cli import app
from cryoflow_core.config import CryoflowConfig
from cryoflow_core.loader import PluginLoadError

from .conftest import VALID_TOML, MINIMAL_TOML

runner = CliRunner()


# ---------------------------------------------------------------------------
# Help display
# ---------------------------------------------------------------------------


class TestHelpDisplay:
    def test_no_args_shows_help(self):
        result = runner.invoke(app, [])
        # Typer with no_args_is_help may return 0 or 2 depending on version
        assert result.exit_code in (0, 2)
        assert 'Usage' in result.output or 'usage' in result.output.lower()

    def test_help_flag(self):
        result = runner.invoke(app, ['--help'])
        assert result.exit_code == 0
        assert 'Usage' in result.output

    def test_run_help(self):
        result = runner.invoke(app, ['run', '--help'])
        assert result.exit_code == 0
        assert '--config' in result.output


# ---------------------------------------------------------------------------
# run command - success
# ---------------------------------------------------------------------------


class TestRunSuccess:
    def test_run_with_valid_config(self, tmp_path):
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        with (
            patch('cryoflow_core.cli.load_plugins') as mock_load,
            patch('cryoflow_core.cli.get_transform_plugins') as mock_get_trans,
            patch('cryoflow_core.cli.get_output_plugins') as mock_get_out,
        ):
            mock_load.return_value = pluggy.PluginManager('cryoflow')
            mock_get_trans.return_value = []
            mock_get_out.return_value = []
            result = runner.invoke(app, ['run', '--config', str(config_file)])

        assert result.exit_code == 1
        assert '[ERROR] No output plugin configured' in result.output

    def test_output_contains_input_path(self, tmp_path):
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        with (
            patch('cryoflow_core.cli.load_plugins') as mock_load,
            patch('cryoflow_core.cli.get_transform_plugins'),
            patch('cryoflow_core.cli.get_output_plugins'),
        ):
            mock_load.return_value = pluggy.PluginManager('cryoflow')
            result = runner.invoke(app, ['run', '--config', str(config_file)])

        assert 'input_path' in result.output
        assert '/data/input.parquet' in result.output

    def test_output_contains_output_target(self, tmp_path):
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        with (
            patch('cryoflow_core.cli.load_plugins') as mock_load,
            patch('cryoflow_core.cli.get_transform_plugins'),
            patch('cryoflow_core.cli.get_output_plugins'),
        ):
            mock_load.return_value = pluggy.PluginManager('cryoflow')
            result = runner.invoke(app, ['run', '--config', str(config_file)])

        assert 'output_target' in result.output
        assert '/data/output.parquet' in result.output

    def test_output_contains_plugin_count(self, tmp_path):
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        with (
            patch('cryoflow_core.cli.load_plugins') as mock_load,
            patch('cryoflow_core.cli.get_transform_plugins'),
            patch('cryoflow_core.cli.get_output_plugins'),
        ):
            mock_load.return_value = pluggy.PluginManager('cryoflow')
            result = runner.invoke(app, ['run', '--config', str(config_file)])

        assert '1 plugin(s)' in result.output

    def test_minimal_config(self, tmp_path):
        config_file = tmp_path / 'config.toml'
        config_file.write_text(MINIMAL_TOML)

        with (
            patch('cryoflow_core.cli.load_plugins') as mock_load,
            patch('cryoflow_core.cli.get_transform_plugins') as mock_get_trans,
            patch('cryoflow_core.cli.get_output_plugins') as mock_get_out,
        ):
            mock_load.return_value = pluggy.PluginManager('cryoflow')
            mock_get_trans.return_value = []
            mock_get_out.return_value = []
            result = runner.invoke(app, ['run', '--config', str(config_file)])

        assert result.exit_code == 1
        assert '[ERROR] No output plugin configured' in result.output


# ---------------------------------------------------------------------------
# run command - errors
# ---------------------------------------------------------------------------


class TestRunErrors:
    def test_nonexistent_file(self, tmp_path):
        result = runner.invoke(app, ['run', '--config', str(tmp_path / 'nonexistent.toml')])
        assert result.exit_code != 0

    def test_config_load_error(self, tmp_path):
        config_file = tmp_path / 'bad.toml'
        config_file.write_text('invalid = [[[')

        result = runner.invoke(app, ['run', '--config', str(config_file)])
        assert result.exit_code == 1

    def test_plugin_load_error(self, tmp_path):
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        with patch('cryoflow_core.cli.load_plugins') as mock_load:
            mock_load.side_effect = PluginLoadError('plugin failed to load')
            result = runner.invoke(app, ['run', '--config', str(config_file)])

        assert result.exit_code == 1
        assert 'plugin failed to load' in result.output


# ---------------------------------------------------------------------------
# Default config path
# ---------------------------------------------------------------------------


class TestDefaultConfigPath:
    def test_default_config_path_used(self, tmp_path):
        config_file = tmp_path / 'config.toml'
        config_file.write_text(MINIMAL_TOML)

        with (
            patch(
                'cryoflow_core.cli.get_default_config_path',
                return_value=config_file,
            ) as mock_default,
            patch('cryoflow_core.cli.load_plugins') as mock_load,
            patch('cryoflow_core.cli.get_transform_plugins') as mock_get_trans,
            patch('cryoflow_core.cli.get_output_plugins') as mock_get_out,
        ):
            mock_load.return_value = pluggy.PluginManager('cryoflow')
            mock_get_trans.return_value = []
            mock_get_out.return_value = []
            # Invoke without --config so default path is used
            # We also need to patch load_config to use our file
            with patch('cryoflow_core.cli.load_config') as mock_load_config:
                mock_load_config.return_value = CryoflowConfig(
                    input_path=Path('/data/in.parquet'),
                    output_target='/data/out.parquet',
                    plugins=[],
                )
                result = runner.invoke(app, ['run'])

            mock_default.assert_called_once()
        assert result.exit_code == 1
        assert '[ERROR] No output plugin configured' in result.output
