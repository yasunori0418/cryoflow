"""Tests for CryoflowSpecs method existence."""

from cryoflow_core.hookspecs import CryoflowSpecs


class TestCryoflowSpecsMethods:
    def test_has_register_input_plugins(self):
        assert hasattr(CryoflowSpecs, 'register_input_plugins')
        assert callable(CryoflowSpecs.register_input_plugins)

    def test_has_register_transform_plugins(self):
        assert hasattr(CryoflowSpecs, 'register_transform_plugins')
        assert callable(CryoflowSpecs.register_transform_plugins)

    def test_has_register_output_plugins(self):
        assert hasattr(CryoflowSpecs, 'register_output_plugins')
        assert callable(CryoflowSpecs.register_output_plugins)
