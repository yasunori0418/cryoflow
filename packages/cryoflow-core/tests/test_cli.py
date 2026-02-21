"""Tests for cryoflow_core.cli module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pluggy
import polars as pl
from returns.result import Failure, Success
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

    def test_help_short_flag(self):
        result = runner.invoke(app, ['-h'])
        assert result.exit_code == 0
        assert 'Usage' in result.output

    def test_run_help(self):
        result = runner.invoke(app, ['run', '--help'])
        assert result.exit_code == 0
        assert '--config' in result.output

    def test_run_help_short_flag(self):
        result = runner.invoke(app, ['run', '-h'])
        assert result.exit_code == 0
        assert '--config' in result.output

    def test_check_help_short_flag(self):
        result = runner.invoke(app, ['check', '-h'])
        assert result.exit_code == 0
        assert '--config' in result.output


# ---------------------------------------------------------------------------
# Version display
# ---------------------------------------------------------------------------


class TestVersionDisplay:
    def test_version_flag(self):
        result = runner.invoke(app, ['--version'])
        assert result.exit_code == 0
        assert 'cryoflow version' in result.output
        assert 'cryoflow-plugin-collections version' in result.output

    def test_version_short_flag(self):
        result = runner.invoke(app, ['-v'])
        assert result.exit_code == 0
        assert 'cryoflow version' in result.output
        assert 'cryoflow-plugin-collections version' in result.output


# ---------------------------------------------------------------------------
# run command - success
# ---------------------------------------------------------------------------


class TestRunSuccess:
    def test_run_with_valid_config(self, tmp_path):
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        def mock_get_plugins(_pm, plugin_type):
            from cryoflow_core.plugin import OutputPlugin, TransformPlugin
            if plugin_type is TransformPlugin:
                return []
            elif plugin_type is OutputPlugin:
                return []
            return []

        with (
            patch('cryoflow_core.commands.run.load_plugins') as mock_load,
            patch('cryoflow_core.commands.run.get_plugins', side_effect=mock_get_plugins),
        ):
            mock_load.return_value = pluggy.PluginManager('cryoflow')
            result = runner.invoke(app, ['run', '--config', str(config_file)])

        assert result.exit_code == 1
        assert '[ERROR] No output plugin configured' in result.output

    def test_output_contains_input_path(self, tmp_path):
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        def mock_get_plugins(_pm, _plugin_type):
            return []

        with (
            patch('cryoflow_core.commands.run.load_plugins') as mock_load,
            patch('cryoflow_core.commands.run.get_plugins', side_effect=mock_get_plugins),
        ):
            mock_load.return_value = pluggy.PluginManager('cryoflow')
            result = runner.invoke(app, ['run', '--config', str(config_file)])

        assert 'input_path' in result.output
        assert '/data/input.parquet' in result.output

    def test_output_contains_plugin_count(self, tmp_path):
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        def mock_get_plugins(_pm, _plugin_type):
            return []

        with (
            patch('cryoflow_core.commands.run.load_plugins') as mock_load,
            patch('cryoflow_core.commands.run.get_plugins', side_effect=mock_get_plugins),
        ):
            mock_load.return_value = pluggy.PluginManager('cryoflow')
            result = runner.invoke(app, ['run', '--config', str(config_file)])

        assert '1 plugin(s)' in result.output

    def test_minimal_config(self, tmp_path):
        config_file = tmp_path / 'config.toml'
        config_file.write_text(MINIMAL_TOML)

        def mock_get_plugins(_pm, plugin_type):
            from cryoflow_core.plugin import OutputPlugin, TransformPlugin
            if plugin_type is TransformPlugin:
                return []
            elif plugin_type is OutputPlugin:
                return []
            return []

        with (
            patch('cryoflow_core.commands.run.load_plugins') as mock_load,
            patch('cryoflow_core.commands.run.get_plugins', side_effect=mock_get_plugins),
        ):
            mock_load.return_value = pluggy.PluginManager('cryoflow')
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

        with patch('cryoflow_core.commands.run.load_plugins') as mock_load:
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

        def mock_get_plugins(_pm, plugin_type):
            from cryoflow_core.plugin import OutputPlugin, TransformPlugin
            if plugin_type is TransformPlugin:
                return []
            elif plugin_type is OutputPlugin:
                return []
            return []

        with (
            patch(
                'cryoflow_core.commands.run.get_config_path',
                return_value=config_file,
            ) as mock_default,
            patch('cryoflow_core.commands.run.load_plugins') as mock_load,
            patch('cryoflow_core.commands.run.get_plugins', side_effect=mock_get_plugins),
        ):
            mock_load.return_value = pluggy.PluginManager('cryoflow')
            # Invoke without --config so default path is used
            # We also need to patch load_config to use our file
            with patch('cryoflow_core.commands.run.load_config') as mock_load_config:
                from returns.result import Success
                mock_load_config.return_value = Success(CryoflowConfig(
                    input_path=Path('/data/in.parquet'),
                    plugins=[],
                ))
                result = runner.invoke(app, ['run'])

            mock_default.assert_called_once()
        assert result.exit_code == 1
        assert '[ERROR] No output plugin configured' in result.output


# ---------------------------------------------------------------------------
# check command - success
# ---------------------------------------------------------------------------


class TestCheckSuccess:
    def test_check_config_loaded_message(self, tmp_path):
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        with patch('cryoflow_core.commands.check.load_plugins') as mock_load:
            mock_load.side_effect = PluginLoadError('no real plugin')
            result = runner.invoke(app, ['check', '--config', str(config_file)])

        assert '[CHECK] Config loaded:' in result.output

    def test_check_plugin_count_message(self, tmp_path):
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        def mock_get_plugins(_pm, plugin_type):
            from cryoflow_core.plugin import OutputPlugin, TransformPlugin
            if plugin_type is TransformPlugin:
                return []
            elif plugin_type is OutputPlugin:
                return []
            return []

        with (
            patch('cryoflow_core.commands.check.load_plugins') as mock_load,
            patch('cryoflow_core.commands.check.get_plugins', side_effect=mock_get_plugins),
        ):
            mock_load.return_value = pluggy.PluginManager('cryoflow')
            result = runner.invoke(app, ['check', '--config', str(config_file)])

        assert '[CHECK] Loaded 1 plugin(s) successfully.' in result.output

    def test_check_dry_run_success(self, tmp_path):
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        def mock_get_plugins(_pm, plugin_type):
            from cryoflow_core.plugin import OutputPlugin, TransformPlugin
            if plugin_type is TransformPlugin:
                return []
            elif plugin_type is OutputPlugin:
                return [MagicMock()]
            return []

        with (
            patch('cryoflow_core.commands.check.load_plugins') as mock_load,
            patch('cryoflow_core.commands.check.get_plugins', side_effect=mock_get_plugins),
            patch('cryoflow_core.commands.check.run_dry_run_pipeline') as mock_dry_run,
        ):
            mock_load.return_value = pluggy.PluginManager('cryoflow')
            mock_dry_run.return_value = Success({'col_a': pl.Int64, 'col_b': pl.String})
            result = runner.invoke(app, ['check', '--config', str(config_file)])

        assert result.exit_code == 0
        assert '[SUCCESS] Validation completed successfully' in result.output

    def test_check_outputs_schema(self, tmp_path):
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        def mock_get_plugins(_pm, plugin_type):
            from cryoflow_core.plugin import OutputPlugin, TransformPlugin
            if plugin_type is TransformPlugin:
                return []
            elif plugin_type is OutputPlugin:
                return [MagicMock()]
            return []

        with (
            patch('cryoflow_core.commands.check.load_plugins') as mock_load,
            patch('cryoflow_core.commands.check.get_plugins', side_effect=mock_get_plugins),
            patch('cryoflow_core.commands.check.run_dry_run_pipeline') as mock_dry_run,
        ):
            mock_load.return_value = pluggy.PluginManager('cryoflow')
            mock_dry_run.return_value = Success({'col_a': pl.Int64, 'col_b': pl.String})
            result = runner.invoke(app, ['check', '--config', str(config_file)])

        assert 'col_a' in result.output
        assert 'col_b' in result.output


# ---------------------------------------------------------------------------
# check command - errors
# ---------------------------------------------------------------------------


class TestCheckErrors:
    def test_nonexistent_file(self, tmp_path):
        result = runner.invoke(app, ['check', '--config', str(tmp_path / 'nonexistent.toml')])
        assert result.exit_code != 0

    def test_config_load_error(self, tmp_path):
        config_file = tmp_path / 'bad.toml'
        config_file.write_text('invalid = [[[')

        result = runner.invoke(app, ['check', '--config', str(config_file)])
        assert result.exit_code == 1

    def test_plugin_load_error(self, tmp_path):
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        with patch('cryoflow_core.commands.check.load_plugins') as mock_load:
            mock_load.side_effect = PluginLoadError('plugin failed to load')
            result = runner.invoke(app, ['check', '--config', str(config_file)])

        assert result.exit_code == 1
        assert 'plugin failed to load' in result.output

    def test_no_output_plugin(self, tmp_path):
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        def mock_get_plugins(_pm, plugin_type):
            from cryoflow_core.plugin import OutputPlugin, TransformPlugin
            if plugin_type is TransformPlugin:
                return []
            elif plugin_type is OutputPlugin:
                return []
            return []

        with (
            patch('cryoflow_core.commands.check.load_plugins') as mock_load,
            patch('cryoflow_core.commands.check.get_plugins', side_effect=mock_get_plugins),
        ):
            mock_load.return_value = pluggy.PluginManager('cryoflow')
            result = runner.invoke(app, ['check', '--config', str(config_file)])

        assert result.exit_code == 1
        assert '[ERROR] No output plugin configured' in result.output

    def test_multiple_output_plugins(self, tmp_path):
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        def mock_get_plugins(_pm, plugin_type):
            from cryoflow_core.plugin import OutputPlugin, TransformPlugin
            if plugin_type is TransformPlugin:
                return []
            elif plugin_type is OutputPlugin:
                return [MagicMock(), MagicMock()]
            return []

        with (
            patch('cryoflow_core.commands.check.load_plugins') as mock_load,
            patch('cryoflow_core.commands.check.get_plugins', side_effect=mock_get_plugins),
        ):
            mock_load.return_value = pluggy.PluginManager('cryoflow')
            result = runner.invoke(app, ['check', '--config', str(config_file)])

        assert result.exit_code == 1
        assert '[ERROR] Multiple output plugins not supported yet' in result.output

    def test_dry_run_failure(self, tmp_path):
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        def mock_get_plugins(_pm, plugin_type):
            from cryoflow_core.plugin import OutputPlugin, TransformPlugin
            if plugin_type is TransformPlugin:
                return []
            elif plugin_type is OutputPlugin:
                return [MagicMock()]
            return []

        with (
            patch('cryoflow_core.commands.check.load_plugins') as mock_load,
            patch('cryoflow_core.commands.check.get_plugins', side_effect=mock_get_plugins),
            patch('cryoflow_core.commands.check.run_dry_run_pipeline') as mock_dry_run,
        ):
            mock_load.return_value = pluggy.PluginManager('cryoflow')
            mock_dry_run.return_value = Failure(ValueError('schema mismatch'))
            result = runner.invoke(app, ['check', '--config', str(config_file)])

        assert result.exit_code == 1
        assert '[ERROR] Validation failed:' in result.output


# ---------------------------------------------------------------------------
# check command - default config path
# ---------------------------------------------------------------------------


class TestCheckDefaultConfigPath:
    def test_default_config_path_used(self, tmp_path):
        config_file = tmp_path / 'config.toml'
        config_file.write_text(MINIMAL_TOML)

        def mock_get_plugins(_pm, plugin_type):
            from cryoflow_core.plugin import OutputPlugin, TransformPlugin
            if plugin_type is TransformPlugin:
                return []
            elif plugin_type is OutputPlugin:
                return []
            return []

        with (
            patch(
                'cryoflow_core.commands.check.get_config_path',
                return_value=config_file,
            ) as mock_default,
            patch('cryoflow_core.commands.check.load_plugins') as mock_load,
            patch('cryoflow_core.commands.check.get_plugins', side_effect=mock_get_plugins),
        ):
            mock_load.return_value = pluggy.PluginManager('cryoflow')
            with patch('cryoflow_core.commands.check.load_config') as mock_load_config:
                mock_load_config.return_value = Success(CryoflowConfig(
                    input_path=Path('/data/in.parquet'),
                    plugins=[],
                ))
                result = runner.invoke(app, ['check'])

            mock_default.assert_called_once()
        assert result.exit_code == 1
        assert '[ERROR] No output plugin configured' in result.output
