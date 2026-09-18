"""Tests for run command success cases."""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pluggy
from returns.result import Success
from typer.testing import CliRunner

from cryoflow_core.cli import app

from ..conftest import MINIMAL_TOML, VALID_TOML

runner = CliRunner()


class TestRunSuccess:
    def test_run_with_valid_config_no_input(self, tmp_path: Path) -> None:
        """Without input plugin mocked, command should report 'No input plugin configured'."""
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        def mock_get_plugins(_pm: Any, _plugin_type: Any) -> list[Any]:
            return []

        with (
            patch('cryoflow_core.commands.utils.load_plugins') as mock_load,
            patch('cryoflow_core.commands.utils.get_plugins', side_effect=mock_get_plugins),
        ):
            mock_load.return_value = Success(pluggy.PluginManager('cryoflow'))
            result = runner.invoke(app, ['run', '--config', str(config_file)])

        assert result.exit_code == 1
        assert '[ERROR] No input plugin configured' in result.output

    def test_run_with_valid_config_no_output(self, tmp_path: Path) -> None:
        """With input plugin but no output plugin, should report 'No output plugin configured'."""
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        def mock_get_plugins(_pm: Any, plugin_type: Any) -> list[Any]:
            from unittest.mock import MagicMock

            from cryoflow_core.plugin import InputPlugin

            if plugin_type is InputPlugin:
                return [MagicMock()]
            return []

        with (
            patch('cryoflow_core.commands.utils.load_plugins') as mock_load,
            patch('cryoflow_core.commands.utils.get_plugins', side_effect=mock_get_plugins),
        ):
            mock_load.return_value = Success(pluggy.PluginManager('cryoflow'))
            result = runner.invoke(app, ['run', '--config', str(config_file)])

        assert result.exit_code == 1
        assert '[ERROR] No output plugin configured' in result.output

    def test_output_contains_input_plugins(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        def mock_get_plugins(_pm: Any, plugin_type: Any) -> list[Any]:
            from unittest.mock import MagicMock

            from cryoflow_core.plugin import InputPlugin, OutputPlugin

            if plugin_type is InputPlugin or plugin_type is OutputPlugin:
                return [MagicMock()]
            return []

        with (
            patch('cryoflow_core.commands.utils.load_plugins') as mock_load,
            patch('cryoflow_core.commands.utils.get_plugins', side_effect=mock_get_plugins),
            patch('cryoflow_core.commands.run.run_pipeline') as mock_run_pipeline,
        ):
            mock_load.return_value = Success(pluggy.PluginManager('cryoflow'))
            mock_run_pipeline.return_value = Success(None)
            result = runner.invoke(app, ['run', '--config', str(config_file)])

        assert 'input_plugins' in result.output

    def test_output_contains_plugin_count(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        def mock_get_plugins(_pm: Any, plugin_type: Any) -> list[Any]:
            from unittest.mock import MagicMock

            from cryoflow_core.plugin import InputPlugin, OutputPlugin

            if plugin_type is InputPlugin or plugin_type is OutputPlugin:
                return [MagicMock()]
            return []

        with (
            patch('cryoflow_core.commands.utils.load_plugins') as mock_load,
            patch('cryoflow_core.commands.utils.get_plugins', side_effect=mock_get_plugins),
            patch('cryoflow_core.commands.run.run_pipeline') as mock_run_pipeline,
        ):
            mock_load.return_value = Success(pluggy.PluginManager('cryoflow'))
            mock_run_pipeline.return_value = Success(None)
            result = runner.invoke(app, ['run', '--config', str(config_file)])

        # VALID_TOML has 1 input + 1 transform + 0 output = 2 enabled plugins
        assert 'plugin(s)' in result.output

    def test_minimal_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.toml'
        config_file.write_text(MINIMAL_TOML)

        def mock_get_plugins(_pm: Any, _plugin_type: Any) -> list[Any]:
            return []

        with (
            patch('cryoflow_core.commands.utils.load_plugins') as mock_load,
            patch('cryoflow_core.commands.utils.get_plugins', side_effect=mock_get_plugins),
        ):
            mock_load.return_value = Success(pluggy.PluginManager('cryoflow'))
            result = runner.invoke(app, ['run', '--config', str(config_file)])

        assert result.exit_code == 1
        assert '[ERROR] No input plugin configured' in result.output
