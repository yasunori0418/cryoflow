"""Tests for transformation sample plugins."""

import polars as pl
import pytest
from returns.result import Failure, Success

from cryoflow_plugin_collections.transform.multiplier import ColumnMultiplierPlugin


class TestColumnMultiplierPlugin:
    """Tests for ColumnMultiplierPlugin."""

    def test_execute_with_lazyframe(self, tmp_path) -> None:
        """Test multiplication with LazyFrame input."""
        df = pl.LazyFrame({'value': [10, 20, 30], 'name': ['a', 'b', 'c']})
        plugin = ColumnMultiplierPlugin({'column_name': 'value', 'multiplier': 2}, tmp_path)

        result = plugin.execute(df)

        assert isinstance(result, Success)
        transformed = result.unwrap()
        collected = transformed.collect()
        assert collected['value'].to_list() == [20, 40, 60]
        assert collected['name'].to_list() == ['a', 'b', 'c']

    def test_execute_with_dataframe(self, tmp_path) -> None:
        """Test multiplication with DataFrame input."""
        df = pl.DataFrame({'value': [10, 20, 30], 'name': ['a', 'b', 'c']})
        plugin = ColumnMultiplierPlugin({'column_name': 'value', 'multiplier': 3}, tmp_path)

        result = plugin.execute(df)

        assert isinstance(result, Success)
        transformed = result.unwrap()
        assert transformed.to_dict(as_series=False)['value'] == [30, 60, 90]

    def test_execute_with_float_multiplier(self, tmp_path) -> None:
        """Test multiplication with float coefficient."""
        df = pl.LazyFrame({'value': [10, 20, 30]})
        plugin = ColumnMultiplierPlugin({'column_name': 'value', 'multiplier': 1.5}, tmp_path)

        result = plugin.execute(df)

        assert isinstance(result, Success)
        transformed = result.unwrap()
        collected = transformed.collect()
        assert collected.to_dict(as_series=False)['value'] == [15.0, 30.0, 45.0]

    def test_execute_missing_column_name(self, tmp_path) -> None:
        """Test error when column_name option is missing."""
        df = pl.LazyFrame({'value': [1, 2, 3]})
        plugin = ColumnMultiplierPlugin({'multiplier': 2}, tmp_path)

        result = plugin.execute(df)

        assert isinstance(result, Failure)
        assert isinstance(result.failure(), ValueError)
        assert "column_name" in str(result.failure())

    def test_execute_missing_multiplier(self, tmp_path) -> None:
        """Test error when multiplier option is missing."""
        df = pl.LazyFrame({'value': [1, 2, 3]})
        plugin = ColumnMultiplierPlugin({'column_name': 'value'}, tmp_path)

        result = plugin.execute(df)

        assert isinstance(result, Failure)
        assert isinstance(result.failure(), ValueError)
        assert "multiplier" in str(result.failure())

    def test_execute_column_not_found(self, tmp_path) -> None:
        """Test error when specified column does not exist."""
        df = pl.LazyFrame({'value': [1, 2, 3]})
        plugin = ColumnMultiplierPlugin(
            {'column_name': 'unknown_col', 'multiplier': 2},
            tmp_path
        )

        result = plugin.execute(df)

        # LazyFrame defers error until collection, so execute succeeds
        # but the error would occur at collection time
        assert isinstance(result, Success)
        lazy_result = result.unwrap()
        try:
            if hasattr(lazy_result, 'collect'):
                lazy_result.collect()
            assert False, "Expected ColumnNotFoundError"
        except Exception as e:
            assert "unknown_col" in str(e) or "not found" in str(e)

    def test_dry_run_success(self, tmp_path) -> None:
        """Test successful dry_run validation."""
        schema = {'value': pl.Int64(), 'name': pl.Utf8()}
        plugin = ColumnMultiplierPlugin({'column_name': 'value', 'multiplier': 2}, tmp_path)

        result = plugin.dry_run(schema)

        assert isinstance(result, Success)
        assert result.unwrap() == schema

    def test_dry_run_missing_column_name(self, tmp_path) -> None:
        """Test dry_run error when column_name is missing."""
        schema = {'value': pl.Int64}
        plugin = ColumnMultiplierPlugin({'multiplier': 2}, tmp_path)

        result = plugin.dry_run(schema)

        assert isinstance(result, Failure)
        assert isinstance(result.failure(), ValueError)

    def test_dry_run_column_not_in_schema(self, tmp_path) -> None:
        """Test dry_run error when column not in schema."""
        schema = {'value': pl.Int64}
        plugin = ColumnMultiplierPlugin(
            {'column_name': 'unknown_col', 'multiplier': 2},
            tmp_path
        )

        result = plugin.dry_run(schema)

        assert isinstance(result, Failure)
        assert isinstance(result.failure(), ValueError)
        assert "not found in schema" in str(result.failure())

    def test_dry_run_non_numeric_column(self, tmp_path) -> None:
        """Test dry_run error when column is not numeric."""
        schema = {'name': pl.Utf8}
        plugin = ColumnMultiplierPlugin({'column_name': 'name', 'multiplier': 2}, tmp_path)

        result = plugin.dry_run(schema)

        assert isinstance(result, Failure)
        assert isinstance(result.failure(), ValueError)
        assert "numeric type" in str(result.failure())

    @pytest.mark.parametrize(
        'dtype',
        [
            pl.Int8(),
            pl.Int16(),
            pl.Int32(),
            pl.Int64(),
            pl.UInt8(),
            pl.UInt16(),
            pl.UInt32(),
            pl.UInt64(),
            pl.Float32(),
            pl.Float64(),
        ],
    )
    def test_dry_run_accepts_numeric_types(self, dtype, tmp_path) -> None:
        """Test dry_run accepts all numeric types."""
        schema = {'value': dtype}
        plugin = ColumnMultiplierPlugin({'column_name': 'value', 'multiplier': 2}, tmp_path)

        result = plugin.dry_run(schema)

        assert isinstance(result, Success)

    def test_name(self, tmp_path) -> None:
        """Test plugin name."""
        plugin = ColumnMultiplierPlugin({}, tmp_path)
        assert plugin.name() == 'column_multiplier'
