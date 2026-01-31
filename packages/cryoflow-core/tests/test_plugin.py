"""Tests for cryoflow_core.plugin module."""

import polars as pl
import pytest
from returns.result import Failure, Success

from cryoflow_core.plugin import BasePlugin, FrameData, OutputPlugin, TransformPlugin

from .conftest import (
    DummyOutputPlugin,
    DummyTransformPlugin,
    FailingTransformPlugin,
)


# ---------------------------------------------------------------------------
# ABC instantiation
# ---------------------------------------------------------------------------


class TestABCInstantiation:
    def test_base_plugin_not_instantiable(self):
        with pytest.raises(TypeError):
            BasePlugin({})  # type: ignore[abstract]

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


# ---------------------------------------------------------------------------
# Options storage
# ---------------------------------------------------------------------------


class TestOptionsStorage:
    def test_transform_plugin_stores_options(self):
        opts = {'threshold': 10}
        p = DummyTransformPlugin(opts)
        assert p.options is opts

    def test_output_plugin_stores_options(self):
        opts = {'format': 'csv'}
        p = DummyOutputPlugin(opts)
        assert p.options is opts

    def test_empty_options(self):
        p = DummyTransformPlugin({})
        assert p.options == {}


# ---------------------------------------------------------------------------
# execute
# ---------------------------------------------------------------------------


class TestExecute:
    def test_transform_success_lazyframe(self, sample_lazyframe):
        p = DummyTransformPlugin({})
        result = p.execute(sample_lazyframe)
        assert isinstance(result, Success)
        assert result.unwrap() is sample_lazyframe

    def test_transform_success_dataframe(self, sample_dataframe):
        p = DummyTransformPlugin({})
        result = p.execute(sample_dataframe)
        assert isinstance(result, Success)
        assert result.unwrap() is sample_dataframe

    def test_transform_failure(self, sample_lazyframe):
        p = FailingTransformPlugin({})
        result = p.execute(sample_lazyframe)
        assert isinstance(result, Failure)
        exc = result.failure()
        assert isinstance(exc, ValueError)
        assert 'intentional failure' in str(exc)

    def test_output_success(self, sample_lazyframe):
        p = DummyOutputPlugin({})
        result = p.execute(sample_lazyframe)
        assert isinstance(result, Success)
        assert result.unwrap() is None


# ---------------------------------------------------------------------------
# dry_run
# ---------------------------------------------------------------------------


class TestDryRun:
    def test_transform_dry_run_success(self):
        p = DummyTransformPlugin({})
        schema = {'a': pl.Int64, 'b': pl.Utf8}
        result = p.dry_run(schema)
        assert isinstance(result, Success)
        assert result.unwrap() == schema

    def test_transform_dry_run_failure(self):
        p = FailingTransformPlugin({})
        schema = {'a': pl.Int64}
        result = p.dry_run(schema)
        assert isinstance(result, Failure)

    def test_output_dry_run_success(self):
        p = DummyOutputPlugin({})
        schema = {'a': pl.Int64}
        result = p.dry_run(schema)
        assert isinstance(result, Success)


# ---------------------------------------------------------------------------
# Inheritance
# ---------------------------------------------------------------------------


class TestInheritance:
    def test_transform_is_base(self):
        assert issubclass(TransformPlugin, BasePlugin)

    def test_output_is_base(self):
        assert issubclass(OutputPlugin, BasePlugin)

    def test_dummy_transform_is_transform(self):
        assert issubclass(DummyTransformPlugin, TransformPlugin)

    def test_dummy_output_is_output(self):
        assert issubclass(DummyOutputPlugin, OutputPlugin)

    def test_isinstance_check(self):
        p = DummyTransformPlugin({})
        assert isinstance(p, BasePlugin)
        assert isinstance(p, TransformPlugin)
        assert not isinstance(p, OutputPlugin)
