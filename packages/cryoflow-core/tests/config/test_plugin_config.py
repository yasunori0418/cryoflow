"""Tests for PluginConfig data model."""

import pytest
from pydantic import ValidationError

from cryoflow_core.config import PluginConfig


class TestPluginConfig:
    def test_all_fields(self):
        pc = PluginConfig(
            name='my_plugin',
            module='my_mod',
            enabled=False,
            label='sales',
            options={'k': 'v'},
        )
        assert pc.name == 'my_plugin'
        assert pc.module == 'my_mod'
        assert pc.enabled is False
        assert pc.label == 'sales'
        assert pc.options == {'k': 'v'}

    def test_defaults(self):
        pc = PluginConfig(name='p', module='m')
        assert pc.enabled is True
        assert pc.label == 'default'
        assert pc.options == {}

    def test_label_default(self):
        pc = PluginConfig(name='p', module='m')
        assert pc.label == 'default'

    def test_label_custom(self):
        pc = PluginConfig(name='p', module='m', label='custom_stream')
        assert pc.label == 'custom_stream'

    def test_missing_name(self):
        with pytest.raises(ValidationError):
            PluginConfig(module='m')  # type: ignore[call-arg]

    def test_missing_module(self):
        with pytest.raises(ValidationError):
            PluginConfig(name='p')  # type: ignore[call-arg]
