"""Tests for plugin inheritance relationships."""

from pathlib import Path

from cryoflow_core.plugin import BasePlugin, InputPlugin, OutputPlugin, TransformPlugin

from ..conftest import DummyInputPlugin, DummyOutputPlugin, DummyTransformPlugin


class TestInheritance:
    def test_input_is_base(self):
        assert issubclass(InputPlugin, BasePlugin)

    def test_transform_is_base(self):
        assert issubclass(TransformPlugin, BasePlugin)

    def test_output_is_base(self):
        assert issubclass(OutputPlugin, BasePlugin)

    def test_dummy_input_is_input(self):
        assert issubclass(DummyInputPlugin, InputPlugin)

    def test_dummy_transform_is_transform(self):
        assert issubclass(DummyTransformPlugin, TransformPlugin)

    def test_dummy_output_is_output(self):
        assert issubclass(DummyOutputPlugin, OutputPlugin)

    def test_isinstance_check_input(self, tmp_path: Path):
        p = DummyInputPlugin({}, tmp_path)
        assert isinstance(p, BasePlugin)
        assert isinstance(p, InputPlugin)
        assert not isinstance(p, TransformPlugin)
        assert not isinstance(p, OutputPlugin)

    def test_isinstance_check_transform(self, tmp_path: Path):
        p = DummyTransformPlugin({}, tmp_path)
        assert isinstance(p, BasePlugin)
        assert isinstance(p, TransformPlugin)
        assert not isinstance(p, OutputPlugin)
