"""Tests for InputPlugin execute and dry_run."""

import polars as pl
from returns.result import Success

from ..conftest import DummyInputPlugin


class TestInputPluginExecute:
    def test_input_execute_returns_lazyframe(self, tmp_path):
        p = DummyInputPlugin({}, tmp_path)
        result = p.execute()
        assert isinstance(result, Success)
        assert isinstance(result.unwrap(), pl.LazyFrame)

    def test_input_dry_run_returns_schema(self, tmp_path):
        p = DummyInputPlugin({}, tmp_path)
        result = p.dry_run()
        assert isinstance(result, Success)
        schema = result.unwrap()
        assert 'a' in schema
        assert 'b' in schema
        assert schema['a'] == pl.Int64
        assert schema['b'] == pl.String
