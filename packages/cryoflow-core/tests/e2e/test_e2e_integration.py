"""End-to-end integration tests for cryoflow pipeline."""

from pathlib import Path
from tempfile import TemporaryDirectory

import polars as pl
from returns.result import Success

from cryoflow_core.pipeline import run_pipeline


class TestE2EIntegration:
    """End-to-end tests using real plugins and data."""

    def test_parquet_transform_parquet_pipeline(self) -> None:
        """Test complete pipeline: Parquet -> Transform -> Parquet."""
        from cryoflow_plugin_collections.input.parquet_scan import ParquetScanPlugin
        from cryoflow_plugin_collections.output.parquet_writer import ParquetWriterPlugin
        from cryoflow_plugin_collections.transform.multiplier import ColumnMultiplierPlugin

        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            # Create input file
            input_file = tmpdir_path / 'input.parquet'
            input_df = pl.DataFrame({'amount': [100, 200, 300], 'item': ['a', 'b', 'c']})
            input_df.write_parquet(input_file)

            # Set up plugins
            input_plugin = ParquetScanPlugin({'input_path': str(input_file)}, tmpdir_path)
            multiplier_plugin = ColumnMultiplierPlugin({'column_name': 'amount', 'multiplier': 2}, tmpdir_path)
            output_file = tmpdir_path / 'output.parquet'
            output_plugin = ParquetWriterPlugin({'output_path': str(output_file)}, tmpdir_path)

            # Run pipeline
            result = run_pipeline([input_plugin], [multiplier_plugin], [output_plugin])

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
        from cryoflow_plugin_collections.input.ipc_scan import IpcScanPlugin
        from cryoflow_plugin_collections.output.parquet_writer import ParquetWriterPlugin

        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            # Create IPC input file
            input_file = tmpdir_path / 'input.ipc'
            input_df = pl.DataFrame({'value': [1, 2, 3], 'name': ['x', 'y', 'z']})
            input_df.write_ipc(input_file)

            # Set up plugins (no transform)
            input_plugin = IpcScanPlugin({'input_path': str(input_file)}, tmpdir_path)
            output_file = tmpdir_path / 'output.parquet'
            output_plugin = ParquetWriterPlugin({'output_path': str(output_file)}, tmpdir_path)

            # Run pipeline
            result = run_pipeline([input_plugin], [], [output_plugin])

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
        from cryoflow_plugin_collections.input.parquet_scan import ParquetScanPlugin
        from cryoflow_plugin_collections.output.parquet_writer import ParquetWriterPlugin
        from cryoflow_plugin_collections.transform.multiplier import ColumnMultiplierPlugin

        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            # Create input file
            input_file = tmpdir_path / 'input.parquet'
            input_df = pl.DataFrame({'value': [10, 20, 30]})
            input_df.write_parquet(input_file)

            # Set up two transformation plugins
            input_plugin = ParquetScanPlugin({'input_path': str(input_file)}, tmpdir_path)
            multiply_2 = ColumnMultiplierPlugin({'column_name': 'value', 'multiplier': 2}, tmpdir_path)
            multiply_3 = ColumnMultiplierPlugin({'column_name': 'value', 'multiplier': 3}, tmpdir_path)
            output_file = tmpdir_path / 'output.parquet'
            output_plugin = ParquetWriterPlugin({'output_path': str(output_file)}, tmpdir_path)

            # Run pipeline (10 * 2 * 3 = 60, 20 * 2 * 3 = 120, 30 * 2 * 3 = 180)
            result = run_pipeline([input_plugin], [multiply_2, multiply_3], [output_plugin])

            # Verify result
            assert isinstance(result, Success)
            output_df = pl.read_parquet(output_file)
            assert output_df.to_dict(as_series=False)['value'] == [60, 120, 180]

    def test_pipeline_with_subdirectory_output(self) -> None:
        """Test pipeline creates subdirectories for output."""
        from cryoflow_plugin_collections.input.parquet_scan import ParquetScanPlugin
        from cryoflow_plugin_collections.output.parquet_writer import ParquetWriterPlugin

        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            # Create input file
            input_file = tmpdir_path / 'input.parquet'
            input_df = pl.DataFrame({'data': [1, 2, 3]})
            input_df.write_parquet(input_file)

            # Output to nested directory
            input_plugin = ParquetScanPlugin({'input_path': str(input_file)}, tmpdir_path)
            output_file = tmpdir_path / 'results' / 'nested' / 'output.parquet'
            output_plugin = ParquetWriterPlugin({'output_path': str(output_file)}, tmpdir_path)

            # Run pipeline
            result = run_pipeline([input_plugin], [], [output_plugin])

            # Verify result
            assert isinstance(result, Success)
            assert output_file.exists()

    def test_relative_path_resolution_in_config(self) -> None:
        """Test that relative paths in config are resolved relative to config directory."""
        from cryoflow_core.config import load_config
        from cryoflow_core.loader import get_plugins, load_plugins
        from cryoflow_core.plugin import InputPlugin, OutputPlugin

        with TemporaryDirectory() as tmpdir:
            # Create project structure:
            # tmpdir/
            #   config_dir/
            #     config.toml
            #     data/
            #       input.parquet
            #       output/
            config_dir = Path(tmpdir) / 'config_dir'
            config_dir.mkdir()
            data_dir = config_dir / 'data'
            data_dir.mkdir()
            output_dir = data_dir / 'output'
            output_dir.mkdir()

            # Create input file
            input_file = data_dir / 'input.parquet'
            input_df = pl.DataFrame({'value': [100, 200, 300]})
            input_df.write_parquet(input_file)

            # Create config with relative paths using input_plugins
            config_file = config_dir / 'config.toml'
            config_content = """\
transform_plugins = []

[[input_plugins]]
name = "parquet_scan"
module = "cryoflow_plugin_collections.input.parquet_scan"
enabled = true

[input_plugins.options]
input_path = "data/input.parquet"

[[output_plugins]]
name = "parquet_writer"
module = "cryoflow_plugin_collections.output.parquet_writer"
enabled = true

[output_plugins.options]
output_path = "data/output/result.parquet"
"""
            config_file.write_text(config_content)

            # Load config
            config_result = load_config(config_file)
            assert isinstance(config_result, Success)
            cfg = config_result.unwrap()

            # Verify input plugin config
            assert len(cfg.input_plugins) == 1
            assert cfg.input_plugins[0].options['input_path'] == 'data/input.parquet'

            # Load plugins and verify they can resolve paths
            pm = load_plugins(cfg, config_file)
            input_plugins = get_plugins(pm, InputPlugin)
            output_plugins = get_plugins(pm, OutputPlugin)

            assert len(input_plugins) == 1
            assert len(output_plugins) == 1

            # Run pipeline (this will test that plugins resolve paths correctly)
            result = run_pipeline(input_plugins, [], output_plugins)

            # Verify result
            assert isinstance(result, Success)
            expected_output = (config_dir / 'data' / 'output' / 'result.parquet').resolve()
            assert expected_output.exists()

            # Verify output content
            output_df = pl.read_parquet(expected_output)
            assert output_df.to_dict(as_series=False) == {'value': [100, 200, 300]}
