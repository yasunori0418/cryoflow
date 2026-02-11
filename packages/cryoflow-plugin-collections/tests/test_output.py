"""Tests for output sample plugins."""

from pathlib import Path
from tempfile import TemporaryDirectory

import polars as pl
import pytest
from returns.result import Failure, Success

from cryoflow_plugin_collections.output.parquet_writer import ParquetWriterPlugin


class TestParquetWriterPlugin:
    """Tests for ParquetWriterPlugin."""

    def test_execute_with_lazyframe(self) -> None:
        """Test writing LazyFrame to Parquet."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            output_path = tmpdir_path / 'output.parquet'
            df = pl.LazyFrame({'value': [10, 20, 30], 'name': ['a', 'b', 'c']})
            plugin = ParquetWriterPlugin({'output_path': str(output_path)}, tmpdir_path)

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
            tmpdir_path = Path(tmpdir)
            output_path = tmpdir_path / 'output.parquet'
            df = pl.DataFrame({'value': [10, 20, 30], 'name': ['a', 'b', 'c']})
            plugin = ParquetWriterPlugin({'output_path': str(output_path)}, tmpdir_path)

            result = plugin.execute(df)

            assert isinstance(result, Success)
            assert output_path.exists()

    def test_execute_creates_parent_directory(self) -> None:
        """Test that parent directory is created if needed."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            output_path = tmpdir_path / 'subdir' / 'output.parquet'
            df = pl.DataFrame({'value': [1, 2, 3]})
            plugin = ParquetWriterPlugin({'output_path': str(output_path)}, tmpdir_path)

            result = plugin.execute(df)

            assert isinstance(result, Success)
            assert output_path.exists()

    def test_execute_missing_output_path(self) -> None:
        """Test error when output_path option is missing."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            df = pl.DataFrame({'value': [1, 2, 3]})
            plugin = ParquetWriterPlugin({}, tmpdir_path)

        result = plugin.execute(df)

        assert isinstance(result, Failure)
        assert isinstance(result.failure(), ValueError)
        assert "output_path" in str(result.failure())

    def test_execute_overwrites_existing_file(self) -> None:
        """Test that existing file is overwritten."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            output_path = tmpdir_path / 'output.parquet'
            # Create initial file
            initial_df = pl.DataFrame({'old': [999]})
            initial_df.write_parquet(output_path)

            # Overwrite with new data
            new_df = pl.DataFrame({'new': [1, 2, 3]})
            plugin = ParquetWriterPlugin({'output_path': str(output_path)}, tmpdir_path)
            result = plugin.execute(new_df)

            assert isinstance(result, Success)
            read_back = pl.read_parquet(output_path)
            assert 'new' in read_back.columns
            assert 'old' not in read_back.columns

    def test_dry_run_success(self) -> None:
        """Test successful dry_run validation."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            output_path = tmpdir_path / 'output.parquet'
            schema = {'value': pl.Int64(), 'name': pl.Utf8()}
            plugin = ParquetWriterPlugin({'output_path': str(output_path)}, tmpdir_path)

            result = plugin.dry_run(schema)

            assert isinstance(result, Success)
            assert result.unwrap() == schema

    def test_dry_run_missing_output_path(self) -> None:
        """Test dry_run error when output_path is missing."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            schema = {'value': pl.Int64()}
            plugin = ParquetWriterPlugin({}, tmpdir_path)

            result = plugin.dry_run(schema)

            assert isinstance(result, Failure)
            assert isinstance(result.failure(), ValueError)

    def test_dry_run_creates_parent_directory(self) -> None:
        """Test dry_run creates parent directory for validation."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            output_path = tmpdir_path / 'subdir' / 'output.parquet'
            schema = {'value': pl.Int64()}
            plugin = ParquetWriterPlugin({'output_path': str(output_path)}, tmpdir_path)

            result = plugin.dry_run(schema)

            assert isinstance(result, Success)
            # Parent directory should exist after dry_run
            assert output_path.parent.exists()

    def test_name(self) -> None:
        """Test plugin name."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            plugin = ParquetWriterPlugin({'output_path': '/tmp/test.parquet'}, tmpdir_path)
            assert plugin.name() == 'parquet_writer'

    def test_execute_with_relative_path(self) -> None:
        """Test that relative paths are resolved relative to config_dir."""
        with TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / 'config'
            config_dir.mkdir()
            output_subdir = config_dir / 'output'
            output_subdir.mkdir()

            # Use relative path
            df = pl.DataFrame({'value': [1, 2, 3]})
            plugin = ParquetWriterPlugin({'output_path': 'output/result.parquet'}, config_dir)

            result = plugin.execute(df)

            assert isinstance(result, Success)
            # File should be created relative to config_dir
            expected_path = output_subdir / 'result.parquet'
            assert expected_path.exists()

    def test_dry_run_with_relative_path(self) -> None:
        """Test dry_run with relative paths resolved relative to config_dir."""
        with TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / 'config'
            config_dir.mkdir()

            schema = {'value': pl.Int64()}
            plugin = ParquetWriterPlugin({'output_path': 'data/output.parquet'}, config_dir)

            result = plugin.dry_run(schema)

            assert isinstance(result, Success)
            # Parent directory should exist relative to config_dir
            expected_parent = config_dir / 'data'
            assert expected_parent.exists()
