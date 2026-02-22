"""Tests for load_plugins function."""

from pathlib import Path

import pluggy
import pytest

from cryoflow_core.config import CryoflowConfig, PluginConfig
from cryoflow_core.hookspecs import CryoflowSpecs
from cryoflow_core.loader import PluginLoadError, get_plugins, load_plugins
from cryoflow_core.plugin import InputPlugin, OutputPlugin, TransformPlugin


class TestLoadPlugins:
    def _make_config(
        self,
        input_plugins: list[PluginConfig] | None = None,
        transform_plugins: list[PluginConfig] | None = None,
        output_plugins: list[PluginConfig] | None = None,
    ) -> CryoflowConfig:
        return CryoflowConfig(
            input_plugins=input_plugins or [],
            transform_plugins=transform_plugins or [],
            output_plugins=output_plugins or [],
        )

    def test_empty_plugins(self, tmp_path: Path):
        cfg = self._make_config()
        config_file = tmp_path / 'config.toml'
        config_file.write_text('')
        pm = load_plugins(cfg, config_file)
        assert isinstance(pm, pluggy.PluginManager)

    def test_disabled_plugin_skipped(self, tmp_path: Path, plugin_py_file: Path):
        cfg = self._make_config(
            transform_plugins=[
                PluginConfig(
                    name='skipped',
                    module=str(plugin_py_file),
                    enabled=False,
                )
            ]
        )
        config_file = tmp_path / 'config.toml'
        config_file.write_text('')
        pm = load_plugins(cfg, config_file)
        transforms = get_plugins(pm, TransformPlugin)
        assert len(transforms) == 0

    def test_input_plugin_loaded(self, tmp_path, input_plugin_py_file: Path):
        cfg = self._make_config(
            input_plugins=[
                PluginConfig(
                    name='my_input',
                    module=str(input_plugin_py_file),
                    enabled=True,
                )
            ]
        )
        config_file = tmp_path / 'config.toml'
        config_file.write_text('')
        pm = load_plugins(cfg, config_file)
        inputs = get_plugins(pm, InputPlugin)
        assert len(inputs) == 1
        assert inputs[0].name() == 'my_input'

    def test_input_plugin_label_propagated(self, tmp_path: Path, input_plugin_py_file: Path):
        """Test that label from PluginConfig is passed to the plugin instance."""
        cfg = self._make_config(
            input_plugins=[
                PluginConfig(
                    name='my_input',
                    module=str(input_plugin_py_file),
                    enabled=True,
                    label='sales',
                )
            ]
        )
        config_file = tmp_path / 'config.toml'
        config_file.write_text('')
        pm = load_plugins(cfg, config_file)
        inputs = get_plugins(pm, InputPlugin)
        assert len(inputs) == 1
        assert inputs[0].label == 'sales'

    def test_transform_plugin_loaded(self, tmp_path: Path, plugin_py_file: Path):
        cfg = self._make_config(
            transform_plugins=[
                PluginConfig(
                    name='my_transform',
                    module=str(plugin_py_file),
                    enabled=True,
                )
            ]
        )
        config_file = tmp_path / 'config.toml'
        config_file.write_text('')
        pm = load_plugins(cfg, config_file)
        transforms = get_plugins(pm, TransformPlugin)
        assert len(transforms) == 1
        assert transforms[0].name() == 'my_transform'

    def test_output_plugin_loaded(self, tmp_path: Path, output_plugin_py_file: Path):
        cfg = self._make_config(
            output_plugins=[
                PluginConfig(
                    name='my_output',
                    module=str(output_plugin_py_file),
                    enabled=True,
                )
            ]
        )
        config_file = tmp_path / 'config.toml'
        config_file.write_text('')
        pm = load_plugins(cfg, config_file)
        outputs = get_plugins(pm, OutputPlugin)
        assert len(outputs) == 1
        assert outputs[0].name() == 'my_output'

    def test_existing_pm_accepted(self, tmp_path: Path):
        cfg = self._make_config()
        config_file = tmp_path / 'config.toml'
        config_file.write_text('')
        existing_pm = pluggy.PluginManager('cryoflow')
        existing_pm.add_hookspecs(CryoflowSpecs)
        pm = load_plugins(cfg, config_file, pm=existing_pm)
        assert pm is existing_pm

    def test_plugin_load_error_propagates(self, tmp_path: Path):
        cfg = self._make_config(
            transform_plugins=[
                PluginConfig(
                    name='bad',
                    module=str(tmp_path / 'nonexistent.py'),
                    enabled=True,
                )
            ]
        )
        config_file = tmp_path / 'config.toml'
        config_file.write_text('')
        with pytest.raises(PluginLoadError):
            load_plugins(cfg, config_file)

    def test_dotpath_plugin_loaded(self, tmp_path: Path):
        """Test the dotpath branch of _load_single_plugin (loader.py:158)."""
        cfg = self._make_config(
            transform_plugins=[
                PluginConfig(
                    name='dotpath_plugin',
                    module='tests.dotpath_test_plugin',
                    enabled=True,
                )
            ]
        )
        config_file = tmp_path / 'config.toml'
        config_file.write_text('')
        pm = load_plugins(cfg, config_file)
        transforms = get_plugins(pm, TransformPlugin)
        assert len(transforms) == 1
        assert transforms[0].name() == 'dotpath_transform'

    def test_both_plugin_types(self, tmp_path: Path, plugin_py_file: Path, output_plugin_py_file: Path):
        cfg = self._make_config(
            transform_plugins=[
                PluginConfig(
                    name='my_transform',
                    module=str(plugin_py_file),
                    enabled=True,
                )
            ],
            output_plugins=[
                PluginConfig(
                    name='my_output',
                    module=str(output_plugin_py_file),
                    enabled=True,
                )
            ],
        )
        config_file = tmp_path / 'config.toml'
        config_file.write_text('')
        pm = load_plugins(cfg, config_file)
        transforms = get_plugins(pm, TransformPlugin)
        outputs = get_plugins(pm, OutputPlugin)
        assert len(transforms) == 1
        assert len(outputs) == 1
