"""Tests for run command error cases."""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from cryoflow_core.cli import app
from cryoflow_core.loader import PluginLoadError

from ..conftest import VALID_TOML

runner = CliRunner()


class TestRunErrors:
    def test_nonexistent_file(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ['run', '--config', str(tmp_path / 'nonexistent.toml')])
        assert result.exit_code != 0

    def test_config_load_error(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'bad.toml'
        config_file.write_text('invalid = [[[')

        result = runner.invoke(app, ['run', '--config', str(config_file)])
        assert result.exit_code == 1

    def test_plugin_load_error(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        with patch('cryoflow_core.commands.run.load_plugins') as mock_load:
            mock_load.side_effect = PluginLoadError('plugin failed to load')
            result = runner.invoke(app, ['run', '--config', str(config_file)])

        assert result.exit_code == 1
        assert 'plugin failed to load' in result.output
