"""Tests for plugin dry_run methods."""

from pathlib import Path

import polars as pl
from returns.result import Failure, Success

from ..conftest import DummyOutputPlugin, DummyTransformPlugin, FailingTransformPlugin


class TestDryRun:
    def test_transform_dry_run_success(self, tmp_path: Path):
        p = DummyTransformPlugin({}, tmp_path)
        schema = {'a': pl.Int64(), 'b': pl.Utf8()}
        result = p.dry_run(schema)
        assert isinstance(result, Success)
        assert result.unwrap() == schema

    def test_transform_dry_run_failure(self, tmp_path: Path):
        p = FailingTransformPlugin({}, tmp_path)
        schema: dict[str, pl.DataType] = {'a': pl.Int64()}
        result = p.dry_run(schema)
        assert isinstance(result, Failure)

    def test_output_dry_run_success(self, tmp_path: Path):
        p = DummyOutputPlugin({}, tmp_path)
        schema: dict[str, pl.DataType] = {'a': pl.Int64()}
        result = p.dry_run(schema)
        assert isinstance(result, Success)
