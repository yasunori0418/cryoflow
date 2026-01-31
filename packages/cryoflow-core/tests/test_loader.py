"""Tests for cryoflow_core.loader module."""

import sys
import types
from pathlib import Path
from unittest.mock import patch

import pluggy
import pytest

from cryoflow_core.config import CryoflowConfig, PluginConfig
from cryoflow_core.hookspecs import CryoflowSpecs
from cryoflow_core.loader import (
    PluginLoadError,
    _discover_plugin_classes,
    _instantiate_plugins,
    _is_filesystem_path,
    _load_module_from_dotpath,
    _load_module_from_path,
    _PluginHookRelay,
    _resolve_module_path,
    get_output_plugins,
    get_transform_plugins,
    load_plugins,
)
from cryoflow_core.plugin import BasePlugin, OutputPlugin, TransformPlugin

from .conftest import (
    BrokenInitPlugin,
    DummyOutputPlugin,
    DummyTransformPlugin,
    FailingTransformPlugin,
)

# ---------------------------------------------------------------------------
# Fixtures specific to loader tests
# ---------------------------------------------------------------------------

TRANSFORM_PLUGIN_SOURCE = """\
from typing import Any
import polars as pl
from returns.result import Success, Result
from cryoflow_core.plugin import TransformPlugin, FrameData


class MyTransformPlugin(TransformPlugin):
    def name(self) -> str:
        return "my_transform"

    def execute(self, df: FrameData) -> Result[FrameData, Exception]:
        return Success(df)

    def dry_run(
        self, schema: dict[str, pl.DataType]
    ) -> Result[dict[str, pl.DataType], Exception]:
        return Success(schema)
"""

OUTPUT_PLUGIN_SOURCE = """\
from typing import Any
import polars as pl
from returns.result import Success, Result
from cryoflow_core.plugin import OutputPlugin, FrameData


class MyOutputPlugin(OutputPlugin):
    def name(self) -> str:
        return "my_output"

    def execute(self, df: FrameData) -> Result[None, Exception]:
        return Success(None)

    def dry_run(
        self, schema: dict[str, pl.DataType]
    ) -> Result[dict[str, pl.DataType], Exception]:
        return Success(schema)
"""

BOTH_PLUGINS_SOURCE = TRANSFORM_PLUGIN_SOURCE + "\n" + OUTPUT_PLUGIN_SOURCE

SYNTAX_ERROR_SOURCE = """\
def broken(
    # missing closing paren
"""

EMPTY_MODULE_SOURCE = """\
# No plugins here
x = 42
"""


@pytest.fixture()
def plugin_py_file(tmp_path):
    """Create a .py file with a TransformPlugin implementation."""
    p = tmp_path / "my_plugin.py"
    p.write_text(TRANSFORM_PLUGIN_SOURCE)
    return p


@pytest.fixture()
def output_plugin_py_file(tmp_path):
    """Create a .py file with an OutputPlugin implementation."""
    p = tmp_path / "my_output_plugin.py"
    p.write_text(OUTPUT_PLUGIN_SOURCE)
    return p


@pytest.fixture()
def both_plugins_py_file(tmp_path):
    """Create a .py file with both Transform and Output plugins."""
    p = tmp_path / "both_plugins.py"
    p.write_text(BOTH_PLUGINS_SOURCE)
    return p


@pytest.fixture(autouse=True)
def cleanup_sys_modules():
    """Remove cryoflow_plugin_* entries from sys.modules after each test."""
    yield
    to_remove = [k for k in sys.modules if k.startswith("cryoflow_plugin_")]
    for k in to_remove:
        del sys.modules[k]


# ---------------------------------------------------------------------------
# _is_filesystem_path
# ---------------------------------------------------------------------------


class TestIsFilesystemPath:
    @pytest.mark.parametrize(
        "input_str,expected",
        [
            ("./plugins/my_plugin.py", True),
            ("../plugins/my_plugin.py", True),
            ("/absolute/path/to/plugin.py", True),
            ("relative/path/to/plugin.py", True),
            ("plugin.py", True),
            ("C:\\Windows\\path.py", True),
            (".", True),
            ("my_package.submodule", False),
            ("cryoflow_core.plugin", False),
            ("simple_module", False),
        ],
    )
    def test_patterns(self, input_str, expected):
        assert _is_filesystem_path(input_str) == expected


# ---------------------------------------------------------------------------
# _resolve_module_path
# ---------------------------------------------------------------------------


class TestResolveModulePath:
    def test_relative_path(self, tmp_path):
        plugin_file = tmp_path / "plugins" / "my_plugin.py"
        plugin_file.parent.mkdir(parents=True)
        plugin_file.write_text("# plugin")
        result = _resolve_module_path("plugins/my_plugin.py", tmp_path)
        assert result == plugin_file.resolve()

    def test_absolute_path(self, tmp_path):
        plugin_file = tmp_path / "my_plugin.py"
        plugin_file.write_text("# plugin")
        result = _resolve_module_path(str(plugin_file), tmp_path)
        assert result == plugin_file.resolve()

    def test_nonexistent_path_raises(self, tmp_path):
        with pytest.raises(PluginLoadError, match="does not exist"):
            _resolve_module_path("nonexistent.py", tmp_path)


# ---------------------------------------------------------------------------
# _load_module_from_path
# ---------------------------------------------------------------------------


class TestLoadModuleFromPath:
    def test_loads_module(self, plugin_py_file):
        module = _load_module_from_path("test_plugin", plugin_py_file)
        assert hasattr(module, "MyTransformPlugin")
        assert "cryoflow_plugin_test_plugin" in sys.modules

    def test_syntax_error_raises(self, tmp_path):
        bad_file = tmp_path / "bad.py"
        bad_file.write_text(SYNTAX_ERROR_SOURCE)
        with pytest.raises(PluginLoadError, match="failed to execute module"):
            _load_module_from_path("bad_plugin", bad_file)

    def test_spec_none_raises(self, plugin_py_file):
        with patch(
            "cryoflow_core.loader.importlib.util.spec_from_file_location",
            return_value=None,
        ):
            with pytest.raises(
                PluginLoadError, match="failed to create module spec"
            ):
                _load_module_from_path("spec_none", plugin_py_file)

    def test_syntax_error_cleans_sys_modules(self, tmp_path):
        bad_file = tmp_path / "bad.py"
        bad_file.write_text(SYNTAX_ERROR_SOURCE)
        try:
            _load_module_from_path("bad_cleanup", bad_file)
        except PluginLoadError:
            pass
        assert "cryoflow_plugin_bad_cleanup" not in sys.modules


# ---------------------------------------------------------------------------
# _load_module_from_dotpath
# ---------------------------------------------------------------------------


class TestLoadModuleFromDotpath:
    def test_loads_real_module(self):
        module = _load_module_from_dotpath("cfg", "cryoflow_core.config")
        assert hasattr(module, "CryoflowConfig")

    def test_nonexistent_module_raises(self):
        with pytest.raises(PluginLoadError, match="not found"):
            _load_module_from_dotpath("nope", "nonexistent.module.path")


# ---------------------------------------------------------------------------
# _discover_plugin_classes
# ---------------------------------------------------------------------------


class TestDiscoverPluginClasses:
    def test_discovers_concrete_classes(self):
        mod = types.ModuleType("fake_mod")
        mod.DummyTransformPlugin = DummyTransformPlugin
        mod.DummyOutputPlugin = DummyOutputPlugin
        classes = _discover_plugin_classes("test", mod)
        assert DummyTransformPlugin in classes
        assert DummyOutputPlugin in classes

    def test_excludes_abstract_classes(self):
        mod = types.ModuleType("fake_mod")
        mod.TransformPlugin = TransformPlugin
        mod.DummyTransformPlugin = DummyTransformPlugin
        classes = _discover_plugin_classes("test", mod)
        assert TransformPlugin not in classes
        assert DummyTransformPlugin in classes

    def test_excludes_base_classes(self):
        mod = types.ModuleType("fake_mod")
        mod.BasePlugin = BasePlugin
        mod.DummyTransformPlugin = DummyTransformPlugin
        classes = _discover_plugin_classes("test", mod)
        assert BasePlugin not in classes

    def test_empty_module_raises(self):
        mod = types.ModuleType("empty_mod")
        with pytest.raises(PluginLoadError, match="no BasePlugin subclasses"):
            _discover_plugin_classes("empty", mod)


# ---------------------------------------------------------------------------
# _instantiate_plugins
# ---------------------------------------------------------------------------


class TestInstantiatePlugins:
    def test_normal_instantiation(self):
        opts = {"key": "value"}
        instances = _instantiate_plugins(
            "test", [DummyTransformPlugin, DummyOutputPlugin], opts
        )
        assert len(instances) == 2
        assert all(inst.options is opts for inst in instances)

    def test_options_propagation(self):
        opts = {"threshold": 42}
        instances = _instantiate_plugins("test", [DummyTransformPlugin], opts)
        assert instances[0].options == {"threshold": 42}

    def test_broken_init_raises(self):
        with pytest.raises(PluginLoadError, match="failed to instantiate"):
            _instantiate_plugins("test", [BrokenInitPlugin], {})


# ---------------------------------------------------------------------------
# _PluginHookRelay
# ---------------------------------------------------------------------------


class TestPluginHookRelay:
    def test_register_transform_plugins(self):
        t = DummyTransformPlugin({})
        relay = _PluginHookRelay([t], [])
        assert relay.register_transform_plugins() == [t]

    def test_register_output_plugins(self):
        o = DummyOutputPlugin({})
        relay = _PluginHookRelay([], [o])
        assert relay.register_output_plugins() == [o]

    def test_empty_lists(self):
        relay = _PluginHookRelay([], [])
        assert relay.register_transform_plugins() == []
        assert relay.register_output_plugins() == []


# ---------------------------------------------------------------------------
# load_plugins
# ---------------------------------------------------------------------------


class TestLoadPlugins:
    def _make_config(self, plugins: list[PluginConfig]) -> CryoflowConfig:
        return CryoflowConfig(
            input_path="/data/in.parquet",
            output_target="/data/out.parquet",
            plugins=plugins,
        )

    def test_empty_plugins(self, tmp_path):
        cfg = self._make_config([])
        config_file = tmp_path / "config.toml"
        config_file.write_text("")
        pm = load_plugins(cfg, config_file)
        assert isinstance(pm, pluggy.PluginManager)

    def test_disabled_plugin_skipped(self, tmp_path, plugin_py_file):
        cfg = self._make_config(
            [
                PluginConfig(
                    name="skipped",
                    module=str(plugin_py_file),
                    enabled=False,
                )
            ]
        )
        config_file = tmp_path / "config.toml"
        config_file.write_text("")
        pm = load_plugins(cfg, config_file)
        transforms = get_transform_plugins(pm)
        assert len(transforms) == 0

    def test_transform_plugin_loaded(self, tmp_path, plugin_py_file):
        cfg = self._make_config(
            [
                PluginConfig(
                    name="my_transform",
                    module=str(plugin_py_file),
                    enabled=True,
                )
            ]
        )
        config_file = tmp_path / "config.toml"
        config_file.write_text("")
        pm = load_plugins(cfg, config_file)
        transforms = get_transform_plugins(pm)
        assert len(transforms) == 1
        assert transforms[0].name() == "my_transform"

    def test_output_plugin_loaded(self, tmp_path, output_plugin_py_file):
        cfg = self._make_config(
            [
                PluginConfig(
                    name="my_output",
                    module=str(output_plugin_py_file),
                    enabled=True,
                )
            ]
        )
        config_file = tmp_path / "config.toml"
        config_file.write_text("")
        pm = load_plugins(cfg, config_file)
        outputs = get_output_plugins(pm)
        assert len(outputs) == 1
        assert outputs[0].name() == "my_output"

    def test_existing_pm_accepted(self, tmp_path):
        cfg = self._make_config([])
        config_file = tmp_path / "config.toml"
        config_file.write_text("")
        existing_pm = pluggy.PluginManager("cryoflow")
        existing_pm.add_hookspecs(CryoflowSpecs)
        pm = load_plugins(cfg, config_file, pm=existing_pm)
        assert pm is existing_pm

    def test_plugin_load_error_propagates(self, tmp_path):
        cfg = self._make_config(
            [
                PluginConfig(
                    name="bad",
                    module=str(tmp_path / "nonexistent.py"),
                    enabled=True,
                )
            ]
        )
        config_file = tmp_path / "config.toml"
        config_file.write_text("")
        with pytest.raises(PluginLoadError):
            load_plugins(cfg, config_file)

    def test_dotpath_plugin_loaded(self, tmp_path):
        """Test the dotpath branch of _load_single_plugin (loader.py:158)."""
        cfg = self._make_config(
            [
                PluginConfig(
                    name="dotpath_plugin",
                    module="tests.dotpath_test_plugin",
                    enabled=True,
                )
            ]
        )
        config_file = tmp_path / "config.toml"
        config_file.write_text("")
        pm = load_plugins(cfg, config_file)
        transforms = get_transform_plugins(pm)
        assert len(transforms) == 1
        assert transforms[0].name() == "dotpath_transform"

    def test_both_plugin_types(self, tmp_path, both_plugins_py_file):
        cfg = self._make_config(
            [
                PluginConfig(
                    name="both",
                    module=str(both_plugins_py_file),
                    enabled=True,
                )
            ]
        )
        config_file = tmp_path / "config.toml"
        config_file.write_text("")
        pm = load_plugins(cfg, config_file)
        transforms = get_transform_plugins(pm)
        outputs = get_output_plugins(pm)
        assert len(transforms) == 1
        assert len(outputs) == 1


# ---------------------------------------------------------------------------
# get_transform_plugins / get_output_plugins
# ---------------------------------------------------------------------------


class TestGetPlugins:
    def test_get_transform_plugins_empty(self):
        pm = pluggy.PluginManager("cryoflow")
        pm.add_hookspecs(CryoflowSpecs)
        relay = _PluginHookRelay([], [])
        pm.register(relay)
        assert get_transform_plugins(pm) == []

    def test_get_output_plugins_empty(self):
        pm = pluggy.PluginManager("cryoflow")
        pm.add_hookspecs(CryoflowSpecs)
        relay = _PluginHookRelay([], [])
        pm.register(relay)
        assert get_output_plugins(pm) == []

    def test_get_transform_plugins_with_data(self):
        pm = pluggy.PluginManager("cryoflow")
        pm.add_hookspecs(CryoflowSpecs)
        t = DummyTransformPlugin({})
        relay = _PluginHookRelay([t], [])
        pm.register(relay)
        result = get_transform_plugins(pm)
        assert len(result) == 1
        assert result[0] is t

    def test_get_output_plugins_with_data(self):
        pm = pluggy.PluginManager("cryoflow")
        pm.add_hookspecs(CryoflowSpecs)
        o = DummyOutputPlugin({})
        relay = _PluginHookRelay([], [o])
        pm.register(relay)
        result = get_output_plugins(pm)
        assert len(result) == 1
        assert result[0] is o
