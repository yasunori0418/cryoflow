"""Tests for CryoflowConfig data model."""

import pytest
from pydantic import ValidationError

from cryoflow_core.config import CryoflowConfig, PluginConfig


class TestCryoflowConfig:
    def test_valid(self):
        cfg = CryoflowConfig(
            input_plugins=[PluginConfig(name='p', module='m')],
            transform_plugins=[PluginConfig(name='p2', module='m2')],
            output_plugins=[],
        )
        assert len(cfg.input_plugins) == 1
        assert len(cfg.transform_plugins) == 1
        assert len(cfg.output_plugins) == 0

    def test_missing_input_plugins(self):
        with pytest.raises(ValidationError):
            CryoflowConfig(
                transform_plugins=[],
                output_plugins=[],
            )  # type: ignore[call-arg]

    def test_missing_transform_plugins(self):
        with pytest.raises(ValidationError):
            CryoflowConfig(
                input_plugins=[],
                output_plugins=[],
            )  # type: ignore[call-arg]

    def test_missing_output_plugins(self):
        with pytest.raises(ValidationError):
            CryoflowConfig(
                input_plugins=[],
                transform_plugins=[],
            )  # type: ignore[call-arg]

    def test_empty_input_plugins(self):
        cfg = CryoflowConfig(
            input_plugins=[],
            transform_plugins=[],
            output_plugins=[],
        )
        assert cfg.input_plugins == []
