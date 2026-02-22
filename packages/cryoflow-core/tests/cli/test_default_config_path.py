"""Tests for run command default config path handling."""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pluggy
from returns.result import Success
from typer.testing import CliRunner

from cryoflow_core.cli import app
from cryoflow_core.config import CryoflowConfig

from ..conftest import MINIMAL_TOML

runner = CliRunner()


class TestDefaultConfigPath:
    def test_default_config_path_used(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.toml'
        config_file.write_text(MINIMAL_TOML)

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
            patch(
                'cryoflow_core.commands.run.get_config_path',
                return_value=config_file,
            ) as mock_default,
            patch('cryoflow_core.commands.run.load_plugins') as mock_load,
            patch('cryoflow_core.commands.run.get_plugins', side_effect=mock_get_plugins),
        ):
            mock_load.return_value = pluggy.PluginManager('cryoflow')
            with patch('cryoflow_core.commands.run.load_config') as mock_load_config:
                mock_load_config.return_value = Success(
                    CryoflowConfig(
                        input_plugins=[],
                        transform_plugins=[],
                        output_plugins=[],
                    )
                )
                result = runner.invoke(app, ['run'])

            mock_default.assert_called_once()
        assert result.exit_code == 1
        assert '[ERROR] No input plugin configured' in result.output
