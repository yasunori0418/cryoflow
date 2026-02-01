"""Tests for output sample plugins."""

from pathlib import Path
from tempfile import TemporaryDirectory

import polars as pl
import pytest
from returns.result import Failure, Success

from cryoflow_sample_plugin.output import ParquetWriterPlugin


class TestParquetWriterPlugin:
    """Tests for ParquetWriterPlugin."""

    def test_execute_with_lazyframe(self) -> None:
        """Test writing LazyFrame to Parquet."""
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'output.parquet'
            df = pl.LazyFrame({'value': [10, 20, 30], 'name': ['a', 'b', 'c']})
            plugin = ParquetWriterPlugin({'output_path': str(output_path)})

            result = plugin.execute(df)

            assert isinstance(result, Success)
            assert output_path.exists()
            # Verify content
            read_back = pl.read_parquet(output_path)
            assert read_back.to_dict(as_series=False) == {
                'value': [10, 20, 30],
                'name': ['a', 'b', 'c'],
            }

    def test_execute_with_dataframe(self) -> None:
        """Test writing DataFrame to Parquet."""
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'output.parquet'
            df = pl.DataFrame({'value': [10, 20, 30], 'name': ['a', 'b', 'c']})
            plugin = ParquetWriterPlugin({'output_path': str(output_path)})

            result = plugin.execute(df)

            assert isinstance(result, Success)
            assert output_path.exists()

    def test_execute_creates_parent_directory(self) -> None:
        """Test that parent directory is created if needed."""
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'subdir' / 'output.parquet'
            df = pl.DataFrame({'value': [1, 2, 3]})
            plugin = ParquetWriterPlugin({'output_path': str(output_path)})

            result = plugin.execute(df)

            assert isinstance(result, Success)
            assert output_path.exists()

    def test_execute_missing_output_path(self) -> None:
        """Test error when output_path option is missing."""
        df = pl.DataFrame({'value': [1, 2, 3]})
        plugin = ParquetWriterPlugin({})

        result = plugin.execute(df)

        assert isinstance(result, Failure)
        assert isinstance(result.failure(), ValueError)
        assert "output_path" in str(result.failure())

    def test_execute_overwrites_existing_file(self) -> None:
        """Test that existing file is overwritten."""
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'output.parquet'
            # Create initial file
            initial_df = pl.DataFrame({'old': [999]})
            initial_df.write_parquet(output_path)

            # Overwrite with new data
            new_df = pl.DataFrame({'new': [1, 2, 3]})
            plugin = ParquetWriterPlugin({'output_path': str(output_path)})
            result = plugin.execute(new_df)

            assert isinstance(result, Success)
            read_back = pl.read_parquet(output_path)
            assert 'new' in read_back.columns
            assert 'old' not in read_back.columns

    def test_dry_run_success(self) -> None:
        """Test successful dry_run validation."""
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'output.parquet'
            schema = {'value': pl.Int64(), 'name': pl.Utf8()}
            plugin = ParquetWriterPlugin({'output_path': str(output_path)})

            result = plugin.dry_run(schema)

            assert isinstance(result, Success)
            assert result.unwrap() == schema

    def test_dry_run_missing_output_path(self) -> None:
        """Test dry_run error when output_path is missing."""
        schema = {'value': pl.Int64()}
        plugin = ParquetWriterPlugin({})

        result = plugin.dry_run(schema)

        assert isinstance(result, Failure)
        assert isinstance(result.failure(), ValueError)

    def test_dry_run_creates_parent_directory(self) -> None:
        """Test dry_run creates parent directory for validation."""
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'subdir' / 'output.parquet'
            schema = {'value': pl.Int64()}
            plugin = ParquetWriterPlugin({'output_path': str(output_path)})

            result = plugin.dry_run(schema)

            assert isinstance(result, Success)
            # Parent directory should exist after dry_run
            assert output_path.parent.exists()

    def test_name(self) -> None:
        """Test plugin name."""
        plugin = ParquetWriterPlugin({'output_path': '/tmp/test.parquet'})
        assert plugin.name() == 'parquet_writer'
