"""Tests for check command success cases."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pluggy
import polars as pl
from returns.result import Success
from typer.testing import CliRunner

from cryoflow_core.cli import app

from ..conftest import VALID_TOML

runner = CliRunner(env={"NO_COLOR": "1"})


class TestCheckSuccess:
    def test_check_config_loaded_message(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        with patch('cryoflow_core.commands.check.load_plugins') as mock_load:
            from cryoflow_core.loader import PluginLoadError
            mock_load.side_effect = PluginLoadError('no real plugin')
            result = runner.invoke(app, ['check', '--config', str(config_file)])

        assert '[CHECK] Config loaded:' in result.output

    def test_check_plugin_count_message(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        def mock_get_plugins(_pm: Any, plugin_type: Any) -> list[Any]:
            from cryoflow_core.plugin import InputPlugin, OutputPlugin, TransformPlugin

            if plugin_type is InputPlugin:
                return []
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

        # VALID_TOML has 1 input + 1 transform + 0 output = 2 enabled plugins
        assert '[CHECK] Loaded 2 plugin(s) successfully.' in result.output

    def test_check_dry_run_success(self, tmp_path: Path) -> None:
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
            mock_dry_run.return_value = Success({'col_a': pl.Int64, 'col_b': pl.String})
            result = runner.invoke(app, ['check', '--config', str(config_file)])

        assert result.exit_code == 0
        assert '[SUCCESS] Validation completed successfully' in result.output

    def test_check_outputs_schema(self, tmp_path: Path) -> None:
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
            mock_dry_run.return_value = Success({'col_a': pl.Int64, 'col_b': pl.String})
            result = runner.invoke(app, ['check', '--config', str(config_file)])

        assert 'col_a' in result.output
        assert 'col_b' in result.output
