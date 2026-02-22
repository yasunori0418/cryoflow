"""Tests for check command error cases."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pluggy
import polars as pl
from returns.result import Failure, Success
from typer.testing import CliRunner

from cryoflow_core.cli import app
from cryoflow_core.loader import PluginLoadError

from ..conftest import VALID_TOML

runner = CliRunner()


class TestCheckErrors:
    def test_nonexistent_file(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ['check', '--config', str(tmp_path / 'nonexistent.toml')])
        assert result.exit_code != 0

    def test_config_load_error(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'bad.toml'
        config_file.write_text('invalid = [[[')

        result = runner.invoke(app, ['check', '--config', str(config_file)])
        assert result.exit_code == 1

    def test_plugin_load_error(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        with patch('cryoflow_core.commands.check.load_plugins') as mock_load:
            mock_load.side_effect = PluginLoadError('plugin failed to load')
            result = runner.invoke(app, ['check', '--config', str(config_file)])

        assert result.exit_code == 1
        assert 'plugin failed to load' in result.output

    def test_no_input_plugin(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        def mock_get_plugins(_pm: Any, plugin_type: Any) -> list[Any]:
            from cryoflow_core.plugin import InputPlugin, OutputPlugin, TransformPlugin

            if plugin_type is InputPlugin:
                return []
            elif plugin_type is TransformPlugin:
                return []
            elif plugin_type is OutputPlugin:
                return [MagicMock()]
            return []

        with (
            patch('cryoflow_core.commands.check.load_plugins') as mock_load,
            patch('cryoflow_core.commands.check.get_plugins', side_effect=mock_get_plugins),
        ):
            mock_load.return_value = pluggy.PluginManager('cryoflow')
            result = runner.invoke(app, ['check', '--config', str(config_file)])

        assert result.exit_code == 1
        assert '[ERROR] No input plugin configured' in result.output

    def test_no_output_plugin(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        def mock_get_plugins(_pm: Any, plugin_type: Any) -> list[Any]:
            from cryoflow_core.plugin import InputPlugin, OutputPlugin, TransformPlugin

            if plugin_type is InputPlugin:
                return [MagicMock()]
            elif plugin_type is TransformPlugin:
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

    def test_multiple_output_plugins_succeed(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        def mock_get_plugins(_pm: Any, plugin_type: Any) -> list[Any]:
            from cryoflow_core.plugin import InputPlugin, OutputPlugin, TransformPlugin

            if plugin_type is InputPlugin:
                return [MagicMock()]
            elif plugin_type is TransformPlugin:
                return []
            elif plugin_type is OutputPlugin:
                return [MagicMock(), MagicMock()]
            return []

        with (
            patch('cryoflow_core.commands.check.load_plugins') as mock_load,
            patch('cryoflow_core.commands.check.get_plugins', side_effect=mock_get_plugins),
            patch('cryoflow_core.commands.check.run_dry_run_pipeline') as mock_dry_run,
        ):
            mock_load.return_value = pluggy.PluginManager('cryoflow')
            mock_dry_run.return_value = Success({'col_a': pl.Int64})
            result = runner.invoke(app, ['check', '--config', str(config_file)])

        assert result.exit_code == 0
        assert '[SUCCESS] Validation completed successfully' in result.output

    def test_dry_run_failure(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        def mock_get_plugins(_pm: Any, plugin_type: Any) -> list[Any]:
            from cryoflow_core.plugin import InputPlugin, OutputPlugin, TransformPlugin

            if plugin_type is InputPlugin:
                return [MagicMock()]
            elif plugin_type is TransformPlugin:
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
