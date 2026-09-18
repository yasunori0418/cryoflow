"""Tests for the shared pipeline setup helper."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pluggy
from returns.result import Failure, Success

from cryoflow_core.commands.utils import setup_pipeline
from cryoflow_core.config import ConfigLoadError
from cryoflow_core.loader import PluginLoadError
from cryoflow_core.plugin import InputPlugin, OutputPlugin, TransformPlugin

from ..conftest import VALID_TOML


class TestSetupPipeline:
    def test_success(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        input_plugin = MagicMock()
        transform_plugin = MagicMock()
        output_plugin = MagicMock()

        def mock_get_plugins(_pm: Any, plugin_type: Any) -> list[Any]:
            if plugin_type is InputPlugin:
                return [input_plugin]
            elif plugin_type is TransformPlugin:
                return [transform_plugin]
            elif plugin_type is OutputPlugin:
                return [output_plugin]
            return []

        with (
            patch('cryoflow_core.commands.utils.load_plugins') as mock_load,
            patch('cryoflow_core.commands.utils.get_plugins', side_effect=mock_get_plugins),
        ):
            mock_load.return_value = Success(pluggy.PluginManager('cryoflow'))
            result = setup_pipeline(config_file)

        assert isinstance(result, Success)
        setup = result.unwrap()
        assert setup.config_path == config_file
        assert len(setup.cfg.input_plugins) == 1
        assert setup.input_plugins == [input_plugin]
        assert setup.transform_plugins == [transform_plugin]
        assert setup.output_plugins == [output_plugin]

    def test_config_load_failure(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        error = ConfigLoadError('config is broken')

        with patch('cryoflow_core.commands.utils.load_config') as mock_load_config:
            mock_load_config.return_value = Failure(error)
            result = setup_pipeline(config_file)

        assert isinstance(result, Failure)
        assert result.failure() is error

    def test_plugin_load_failure(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        error = PluginLoadError('plugin failed to load')

        with patch('cryoflow_core.commands.utils.load_plugins') as mock_load:
            mock_load.return_value = Failure(error)
            result = setup_pipeline(config_file)

        assert isinstance(result, Failure)
        assert result.failure() is error

    def test_no_input_plugin(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        def mock_get_plugins(_pm: Any, plugin_type: Any) -> list[Any]:
            if plugin_type is OutputPlugin:
                return [MagicMock()]
            return []

        with (
            patch('cryoflow_core.commands.utils.load_plugins') as mock_load,
            patch('cryoflow_core.commands.utils.get_plugins', side_effect=mock_get_plugins),
        ):
            mock_load.return_value = Success(pluggy.PluginManager('cryoflow'))
            result = setup_pipeline(config_file)

        assert isinstance(result, Failure)
        failure = result.failure()
        assert isinstance(failure, ValueError)
        assert str(failure) == 'No input plugin configured'

    def test_no_output_plugin(self, tmp_path: Path) -> None:
        config_file = tmp_path / 'config.toml'
        config_file.write_text(VALID_TOML)

        def mock_get_plugins(_pm: Any, plugin_type: Any) -> list[Any]:
            if plugin_type is InputPlugin:
                return [MagicMock()]
            return []

        with (
            patch('cryoflow_core.commands.utils.load_plugins') as mock_load,
            patch('cryoflow_core.commands.utils.get_plugins', side_effect=mock_get_plugins),
        ):
            mock_load.return_value = Success(pluggy.PluginManager('cryoflow'))
            result = setup_pipeline(config_file)

        assert isinstance(result, Failure)
        failure = result.failure()
        assert isinstance(failure, ValueError)
        assert str(failure) == 'No output plugin configured'
