"""Tests for cryoflow_core.hookspecs module."""

import pluggy

from cryoflow_core.hookspecs import CryoflowSpecs, hookimpl, hookspec
from cryoflow_core.plugin import OutputPlugin, TransformPlugin

from .conftest import DummyOutputPlugin, DummyTransformPlugin


# ---------------------------------------------------------------------------
# Marker project name
# ---------------------------------------------------------------------------


class TestMarkers:
    def test_hookspec_project_name(self):
        assert hookspec.project_name == "cryoflow"

    def test_hookimpl_project_name(self):
        assert hookimpl.project_name == "cryoflow"


# ---------------------------------------------------------------------------
# CryoflowSpecs methods
# ---------------------------------------------------------------------------


class TestCryoflowSpecsMethods:
    def test_has_register_transform_plugins(self):
        assert hasattr(CryoflowSpecs, "register_transform_plugins")
        assert callable(CryoflowSpecs.register_transform_plugins)

    def test_has_register_output_plugins(self):
        assert hasattr(CryoflowSpecs, "register_output_plugins")
        assert callable(CryoflowSpecs.register_output_plugins)


# ---------------------------------------------------------------------------
# Pluggy integration
# ---------------------------------------------------------------------------


class TestPluggyIntegration:
    def test_hookspec_registration_and_call(self):
        """Register hookspec, add hookimpl, call hook, verify results."""
        pm = pluggy.PluginManager("cryoflow")
        pm.add_hookspecs(CryoflowSpecs)

        transform = DummyTransformPlugin({})

        class MyHookImpl:
            @hookimpl
            def register_transform_plugins(self) -> list[TransformPlugin]:
                return [transform]

        pm.register(MyHookImpl())
        results = pm.hook.register_transform_plugins()
        # pluggy returns a list of lists (one per hookimpl)
        flat = [p for sublist in results for p in sublist]
        assert len(flat) == 1
        assert flat[0] is transform

    def test_output_hookimpl(self):
        pm = pluggy.PluginManager("cryoflow")
        pm.add_hookspecs(CryoflowSpecs)

        output = DummyOutputPlugin({})

        class MyOutputHookImpl:
            @hookimpl
            def register_output_plugins(self) -> list[OutputPlugin]:
                return [output]

        pm.register(MyOutputHookImpl())
        results = pm.hook.register_output_plugins()
        flat = [p for sublist in results for p in sublist]
        assert len(flat) == 1
        assert flat[0] is output

    def test_multiple_hookimpls(self):
        """Multiple hookimpls should all contribute to the result."""
        pm = pluggy.PluginManager("cryoflow")
        pm.add_hookspecs(CryoflowSpecs)

        t1 = DummyTransformPlugin({"id": "1"})
        t2 = DummyTransformPlugin({"id": "2"})

        class Impl1:
            @hookimpl
            def register_transform_plugins(self) -> list[TransformPlugin]:
                return [t1]

        class Impl2:
            @hookimpl
            def register_transform_plugins(self) -> list[TransformPlugin]:
                return [t2]

        pm.register(Impl1())
        pm.register(Impl2())

        results = pm.hook.register_transform_plugins()
        flat = [p for sublist in results for p in sublist]
        assert len(flat) == 2
        assert t1 in flat
        assert t2 in flat
