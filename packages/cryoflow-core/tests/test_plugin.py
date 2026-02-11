"""Tests for cryoflow_core.plugin module."""

from pathlib import Path

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
    def test_transform_plugin_stores_options(self, tmp_path):
        opts = {'threshold': 10}
        p = DummyTransformPlugin(opts, tmp_path)
        assert p.options is opts

    def test_output_plugin_stores_options(self, tmp_path):
        opts = {'format': 'csv'}
        p = DummyOutputPlugin(opts, tmp_path)
        assert p.options is opts

    def test_empty_options(self, tmp_path):
        p = DummyTransformPlugin({}, tmp_path)
        assert p.options == {}


# ---------------------------------------------------------------------------
# execute
# ---------------------------------------------------------------------------


class TestExecute:
    def test_transform_success_lazyframe(self, sample_lazyframe, tmp_path):
        p = DummyTransformPlugin({}, tmp_path)
        result = p.execute(sample_lazyframe)
        assert isinstance(result, Success)
        assert result.unwrap() is sample_lazyframe

    def test_transform_success_dataframe(self, sample_dataframe, tmp_path):
        p = DummyTransformPlugin({}, tmp_path)
        result = p.execute(sample_dataframe)
        assert isinstance(result, Success)
        assert result.unwrap() is sample_dataframe

    def test_transform_failure(self, sample_lazyframe, tmp_path):
        p = FailingTransformPlugin({}, tmp_path)
        result = p.execute(sample_lazyframe)
        assert isinstance(result, Failure)
        exc = result.failure()
        assert isinstance(exc, ValueError)
        assert 'intentional failure' in str(exc)

    def test_output_success(self, sample_lazyframe, tmp_path):
        p = DummyOutputPlugin({}, tmp_path)
        result = p.execute(sample_lazyframe)
        assert isinstance(result, Success)
        assert result.unwrap() is None


# ---------------------------------------------------------------------------
# dry_run
# ---------------------------------------------------------------------------


class TestDryRun:
    def test_transform_dry_run_success(self, tmp_path):
        p = DummyTransformPlugin({}, tmp_path)
        schema = {'a': pl.Int64, 'b': pl.Utf8}
        result = p.dry_run(schema)
        assert isinstance(result, Success)
        assert result.unwrap() == schema

    def test_transform_dry_run_failure(self, tmp_path):
        p = FailingTransformPlugin({}, tmp_path)
        schema = {'a': pl.Int64}
        result = p.dry_run(schema)
        assert isinstance(result, Failure)

    def test_output_dry_run_success(self, tmp_path):
        p = DummyOutputPlugin({}, tmp_path)
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

    def test_isinstance_check(self, tmp_path):
        p = DummyTransformPlugin({}, tmp_path)
        assert isinstance(p, BasePlugin)
        assert isinstance(p, TransformPlugin)
        assert not isinstance(p, OutputPlugin)


# ---------------------------------------------------------------------------
# Path Resolution
# ---------------------------------------------------------------------------


class TestPathResolution:
    def test_resolve_path_relative(self, tmp_path):
        """Test that relative paths are resolved relative to config_dir."""
        config_dir = tmp_path / 'config'
        config_dir.mkdir()
        p = DummyTransformPlugin({}, config_dir)
        result = p.resolve_path('data/output.parquet')
        expected = (config_dir / 'data' / 'output.parquet').resolve()
        assert result == expected

    def test_resolve_path_absolute(self, tmp_path):
        """Test that absolute paths are preserved (after normalization)."""
        config_dir = tmp_path / 'config'
        config_dir.mkdir()
        p = DummyTransformPlugin({}, config_dir)
        absolute_path = Path('/absolute/path/to/file.parquet')
        result = p.resolve_path(absolute_path)
        assert result == absolute_path.resolve()

    def test_resolve_path_string_input(self, tmp_path):
        """Test that string paths work correctly."""
        config_dir = tmp_path / 'config'
        config_dir.mkdir()
        p = DummyTransformPlugin({}, config_dir)
        result = p.resolve_path('relative/path.txt')
        expected = (config_dir / 'relative' / 'path.txt').resolve()
        assert result == expected

    def test_resolve_path_path_input(self, tmp_path):
        """Test that Path objects work correctly."""
        config_dir = tmp_path / 'config'
        config_dir.mkdir()
        p = DummyTransformPlugin({}, config_dir)
        result = p.resolve_path(Path('relative/path.txt'))
        expected = (config_dir / 'relative' / 'path.txt').resolve()
        assert result == expected
