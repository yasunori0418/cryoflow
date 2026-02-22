"""Tests for extract_schema function."""

import polars as pl
from returns.result import Success

from cryoflow_core.pipeline import extract_schema


class TestExtractSchema:
    """Tests for schema extraction."""

    def test_extract_schema_from_lazyframe(self) -> None:
        """Test schema extraction from LazyFrame."""
        df = pl.DataFrame({'a': [1, 2, 3], 'b': ['x', 'y', 'z']})
        lazy_df = df.lazy()
        result = extract_schema(lazy_df)

        assert isinstance(result, Success)
        schema = result.unwrap()
        assert 'a' in schema
        assert 'b' in schema
        assert schema['a'] == pl.Int64
        assert schema['b'] == pl.String

    def test_extract_schema_from_dataframe(self) -> None:
        """Test schema extraction from DataFrame."""
        df = pl.DataFrame({'x': [1.0, 2.0], 'y': [10, 20]})
        result = extract_schema(df)

        assert isinstance(result, Success)
        schema = result.unwrap()
        assert 'x' in schema
        assert 'y' in schema
        assert schema['x'] == pl.Float64
        assert schema['y'] == pl.Int64

    def test_extract_schema_empty_frame(self) -> None:
        """Test schema extraction from empty DataFrame."""
        df = pl.DataFrame({'col1': pl.Series([], dtype=pl.Int32), 'col2': pl.Series([], dtype=pl.String)})
        result = extract_schema(df)

        assert isinstance(result, Success)
        schema = result.unwrap()
        assert 'col1' in schema
        assert 'col2' in schema
        assert schema['col1'] == pl.Int32
        assert schema['col2'] == pl.String
