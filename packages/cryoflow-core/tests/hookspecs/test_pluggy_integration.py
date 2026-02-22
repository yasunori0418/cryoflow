"""Tests for pluggy integration with hookspecs."""

import pluggy

from cryoflow_core.hookspecs import CryoflowSpecs, hookimpl
from cryoflow_core.plugin import InputPlugin, OutputPlugin, TransformPlugin

from ..conftest import DummyInputPlugin, DummyOutputPlugin, DummyTransformPlugin


class TestPluggyIntegration:
    def test_input_hookspec_registration_and_call(self, tmp_path):
        """Register hookspec, add hookimpl for input, call hook, verify results."""
        pm = pluggy.PluginManager('cryoflow')
        pm.add_hookspecs(CryoflowSpecs)

        inp = DummyInputPlugin({}, tmp_path)

        class MyHookImpl:
            @hookimpl
            def register_input_plugins(self) -> list[InputPlugin]:
                return [inp]

        pm.register(MyHookImpl())
        results = pm.hook.register_input_plugins()
        flat = [p for sublist in results for p in sublist]
        assert len(flat) == 1
        assert flat[0] is inp

    def test_hookspec_registration_and_call(self, tmp_path):
        """Register hookspec, add hookimpl, call hook, verify results."""
        pm = pluggy.PluginManager('cryoflow')
        pm.add_hookspecs(CryoflowSpecs)

        transform = DummyTransformPlugin({}, tmp_path)

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

    def test_output_hookimpl(self, tmp_path):
        pm = pluggy.PluginManager('cryoflow')
        pm.add_hookspecs(CryoflowSpecs)

        output = DummyOutputPlugin({}, tmp_path)

        class MyOutputHookImpl:
            @hookimpl
            def register_output_plugins(self) -> list[OutputPlugin]:
                return [output]

        pm.register(MyOutputHookImpl())
        results = pm.hook.register_output_plugins()
        flat = [p for sublist in results for p in sublist]
        assert len(flat) == 1
        assert flat[0] is output

    def test_multiple_hookimpls(self, tmp_path):
        """Multiple hookimpls should all contribute to the result."""
        pm = pluggy.PluginManager('cryoflow')
        pm.add_hookspecs(CryoflowSpecs)

        t1 = DummyTransformPlugin({'id': '1'}, tmp_path)
        t2 = DummyTransformPlugin({'id': '2'}, tmp_path)

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
