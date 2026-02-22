"""Tests for plugin execute methods."""

from pathlib import Path

import polars as pl
from returns.result import Failure, Success

from ..conftest import DummyOutputPlugin, DummyTransformPlugin, FailingTransformPlugin


class TestExecute:
    def test_transform_success_lazyframe(self, sample_lazyframe: pl.LazyFrame, tmp_path: Path):
        p = DummyTransformPlugin({}, tmp_path)
        result = p.execute(sample_lazyframe)
        assert isinstance(result, Success)
        assert result.unwrap() is sample_lazyframe

    def test_transform_success_dataframe(self, sample_dataframe: pl.DataFrame, tmp_path: Path):
        p = DummyTransformPlugin({}, tmp_path)
        result = p.execute(sample_dataframe)
        assert isinstance(result, Success)
        assert result.unwrap() is sample_dataframe

    def test_transform_failure(self, sample_lazyframe: pl.LazyFrame, tmp_path: Path):
        p = FailingTransformPlugin({}, tmp_path)
        result = p.execute(sample_lazyframe)
        assert isinstance(result, Failure)
        exc = result.failure()
        assert isinstance(exc, ValueError)
        assert 'intentional failure' in str(exc)

    def test_output_success(self, sample_lazyframe: pl.LazyFrame, tmp_path: Path):
        p = DummyOutputPlugin({}, tmp_path)
        result = p.execute(sample_lazyframe)
        assert isinstance(result, Success)
        assert result.unwrap() is None
