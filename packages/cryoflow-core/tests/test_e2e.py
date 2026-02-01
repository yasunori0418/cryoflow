"""End-to-end integration tests for cryoflow pipeline."""

from pathlib import Path
from tempfile import TemporaryDirectory

import polars as pl
import pytest
from returns.result import Success

from cryoflow_core.pipeline import run_pipeline


class TestE2EIntegration:
    """End-to-end tests using real plugins and data."""

    def test_parquet_transform_parquet_pipeline(self) -> None:
        """Test complete pipeline: Parquet -> Transform -> Parquet."""
        from cryoflow_sample_plugin.output import ParquetWriterPlugin
        from cryoflow_sample_plugin.transform import ColumnMultiplierPlugin

        with TemporaryDirectory() as tmpdir:
            # Create input file
            input_file = Path(tmpdir) / 'input.parquet'
            input_df = pl.DataFrame(
                {'amount': [100, 200, 300], 'item': ['a', 'b', 'c']}
            )
            input_df.write_parquet(input_file)

            # Set up plugins
            multiplier_plugin = ColumnMultiplierPlugin(
                {'column_name': 'amount', 'multiplier': 2}
            )
            output_file = Path(tmpdir) / 'output.parquet'
            output_plugin = ParquetWriterPlugin({'output_path': str(output_file)})

            # Run pipeline
            result = run_pipeline(
                input_file, [multiplier_plugin], output_plugin
            )

            # Verify result
            assert isinstance(result, Success)
            assert output_file.exists()

            # Verify output content
            output_df = pl.read_parquet(output_file)
            assert output_df.to_dict(as_series=False) == {
                'amount': [200, 400, 600],
                'item': ['a', 'b', 'c'],
            }

    def test_ipc_to_parquet_pipeline(self) -> None:
        """Test pipeline: IPC -> Parquet."""
        from cryoflow_sample_plugin.output import ParquetWriterPlugin

        with TemporaryDirectory() as tmpdir:
            # Create IPC input file
            input_file = Path(tmpdir) / 'input.ipc'
            input_df = pl.DataFrame({'value': [1, 2, 3], 'name': ['x', 'y', 'z']})
            input_df.write_ipc(input_file)

            # Set up plugin (no transform)
            output_file = Path(tmpdir) / 'output.parquet'
            output_plugin = ParquetWriterPlugin({'output_path': str(output_file)})

            # Run pipeline
            result = run_pipeline(input_file, [], output_plugin)

            # Verify result
            assert isinstance(result, Success)
            assert output_file.exists()

            output_df = pl.read_parquet(output_file)
            assert output_df.to_dict(as_series=False) == {
                'value': [1, 2, 3],
                'name': ['x', 'y', 'z'],
            }

    def test_multiple_transforms_pipeline(self) -> None:
        """Test pipeline with multiple transformation plugins."""
        from cryoflow_sample_plugin.output import ParquetWriterPlugin
        from cryoflow_sample_plugin.transform import ColumnMultiplierPlugin

        with TemporaryDirectory() as tmpdir:
            # Create input file
            input_file = Path(tmpdir) / 'input.parquet'
            input_df = pl.DataFrame({'value': [10, 20, 30]})
            input_df.write_parquet(input_file)

            # Set up two transformation plugins
            multiply_2 = ColumnMultiplierPlugin(
                {'column_name': 'value', 'multiplier': 2}
            )
            multiply_3 = ColumnMultiplierPlugin(
                {'column_name': 'value', 'multiplier': 3}
            )
            output_file = Path(tmpdir) / 'output.parquet'
            output_plugin = ParquetWriterPlugin({'output_path': str(output_file)})

            # Run pipeline (10 * 2 * 3 = 60, 20 * 2 * 3 = 120, 30 * 2 * 3 = 180)
            result = run_pipeline(
                input_file, [multiply_2, multiply_3], output_plugin
            )

            # Verify result
            assert isinstance(result, Success)
            output_df = pl.read_parquet(output_file)
            assert output_df.to_dict(as_series=False)['value'] == [60, 120, 180]

    def test_pipeline_with_subdirectory_output(self) -> None:
        """Test pipeline creates subdirectories for output."""
        from cryoflow_sample_plugin.output import ParquetWriterPlugin

        with TemporaryDirectory() as tmpdir:
            # Create input file
            input_file = Path(tmpdir) / 'input.parquet'
            input_df = pl.DataFrame({'data': [1, 2, 3]})
            input_df.write_parquet(input_file)

            # Output to nested directory
            output_file = Path(tmpdir) / 'results' / 'nested' / 'output.parquet'
            output_plugin = ParquetWriterPlugin({'output_path': str(output_file)})

            # Run pipeline
            result = run_pipeline(input_file, [], output_plugin)

            # Verify result
            assert isinstance(result, Success)
            assert output_file.exists()
