"""Tests for ABC instantiation in plugin module."""

import pytest

from cryoflow_core.plugin import BasePlugin, InputPlugin, OutputPlugin, TransformPlugin


class TestABCInstantiation:
    def test_base_plugin_not_instantiable(self):
        with pytest.raises(TypeError):
            BasePlugin({})  # type: ignore[abstract]

    def test_input_plugin_not_instantiable(self):
        with pytest.raises(TypeError):
            InputPlugin({})  # type: ignore[abstract]

    def test_transform_plugin_not_instantiable(self):
        with pytest.raises(TypeError):
            TransformPlugin({})  # type: ignore[abstract]

    def test_output_plugin_not_instantiable(self):
        with pytest.raises(TypeError):
            OutputPlugin({})  # type: ignore[abstract]

    def test_partial_implementation_raises(self):
        """Only implementing name() should still raise TypeError."""

        class PartialPlugin(TransformPlugin):
            def name(self) -> str:
                return 'partial'

        with pytest.raises(TypeError):
            PartialPlugin({})
