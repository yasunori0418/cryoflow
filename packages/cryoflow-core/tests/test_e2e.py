"""End-to-end integration tests for cryoflow pipeline."""

from pathlib import Path
from tempfile import TemporaryDirectory

import polars as pl
from returns.result import Success
from typer.testing import CliRunner

from cryoflow_core.pipeline import run_pipeline
from cryoflow_core.cli import app


class TestE2EIntegration:
    """End-to-end tests using real plugins and data."""

    def test_parquet_transform_parquet_pipeline(self) -> None:
        """Test complete pipeline: Parquet -> Transform -> Parquet."""
        from cryoflow_plugin_collections.output.parquet_writer import ParquetWriterPlugin
        from cryoflow_plugin_collections.transform.multiplier import ColumnMultiplierPlugin

        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            # Create input file
            input_file = tmpdir_path / 'input.parquet'
            input_df = pl.DataFrame(
                {'amount': [100, 200, 300], 'item': ['a', 'b', 'c']}
            )
            input_df.write_parquet(input_file)

            # Set up plugins
            multiplier_plugin = ColumnMultiplierPlugin(
                {'column_name': 'amount', 'multiplier': 2},
                tmpdir_path
            )
            output_file = tmpdir_path / 'output.parquet'
            output_plugin = ParquetWriterPlugin({'output_path': str(output_file)}, tmpdir_path)

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
        from cryoflow_plugin_collections.output.parquet_writer import ParquetWriterPlugin

        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            # Create IPC input file
            input_file = tmpdir_path / 'input.ipc'
            input_df = pl.DataFrame({'value': [1, 2, 3], 'name': ['x', 'y', 'z']})
            input_df.write_ipc(input_file)

            # Set up plugin (no transform)
            output_file = tmpdir_path / 'output.parquet'
            output_plugin = ParquetWriterPlugin({'output_path': str(output_file)}, tmpdir_path)

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
        from cryoflow_plugin_collections.output.parquet_writer import ParquetWriterPlugin
        from cryoflow_plugin_collections.transform.multiplier import ColumnMultiplierPlugin

        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            # Create input file
            input_file = tmpdir_path / 'input.parquet'
            input_df = pl.DataFrame({'value': [10, 20, 30]})
            input_df.write_parquet(input_file)

            # Set up two transformation plugins
            multiply_2 = ColumnMultiplierPlugin(
                {'column_name': 'value', 'multiplier': 2},
                tmpdir_path
            )
            multiply_3 = ColumnMultiplierPlugin(
                {'column_name': 'value', 'multiplier': 3},
                tmpdir_path
            )
            output_file = tmpdir_path / 'output.parquet'
            output_plugin = ParquetWriterPlugin({'output_path': str(output_file)}, tmpdir_path)

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
        from cryoflow_plugin_collections.output.parquet_writer import ParquetWriterPlugin

        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            # Create input file
            input_file = tmpdir_path / 'input.parquet'
            input_df = pl.DataFrame({'data': [1, 2, 3]})
            input_df.write_parquet(input_file)

            # Output to nested directory
            output_file = tmpdir_path / 'results' / 'nested' / 'output.parquet'
            output_plugin = ParquetWriterPlugin({'output_path': str(output_file)}, tmpdir_path)

            # Run pipeline
            result = run_pipeline(input_file, [], output_plugin)

            # Verify result
            assert isinstance(result, Success)
            assert output_file.exists()

    def test_relative_path_resolution_in_config(self) -> None:
        """Test that relative paths in config are resolved relative to config directory."""
        from cryoflow_core.config import load_config
        from cryoflow_core.loader import load_plugins

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

            # Create config with relative paths
            config_file = config_dir / 'config.toml'
            config_content = """\
input_path = "data/input.parquet"

[[plugins]]
name = "parquet_writer"
module = "cryoflow_plugin_collections.output.parquet_writer"
enabled = true

[plugins.options]
output_path = "data/output/result.parquet"
"""
            config_file.write_text(config_content)

            # Load config
            cfg = load_config(config_file)

            # Verify input_path was resolved correctly
            expected_input = (config_dir / 'data' / 'input.parquet').resolve()
            assert cfg.input_path == expected_input

            # Load plugins and verify they can resolve paths
            pm = load_plugins(cfg, config_file)
            from cryoflow_core.loader import get_plugins
            from cryoflow_core.plugin import OutputPlugin
            output_plugins = get_plugins(pm, OutputPlugin)
            assert len(output_plugins) == 1

            # Run pipeline (this will test that output plugin resolves path correctly)
            result = run_pipeline(cfg.input_path, [], output_plugins[0])

            # Verify result
            assert isinstance(result, Success)
            expected_output = (config_dir / 'data' / 'output' / 'result.parquet').resolve()
            assert expected_output.exists()

            # Verify output content
            output_df = pl.read_parquet(expected_output)
            assert output_df.to_dict(as_series=False) == {'value': [100, 200, 300]}


class TestCheckCommand:
    """Tests for the 'check' command CLI."""

    def test_check_command_success(self) -> None:
        """Test successful dry-run check with valid config."""
        from cryoflow_plugin_collections.output.parquet_writer import ParquetWriterPlugin
        from cryoflow_plugin_collections.transform.multiplier import ColumnMultiplierPlugin

        with TemporaryDirectory() as tmpdir:
            # Create input file
            input_file = Path(tmpdir) / 'input.parquet'
            input_df = pl.DataFrame(
                {'amount': [100, 200, 300], 'item': ['a', 'b', 'c']}
            )
            input_df.write_parquet(input_file)

            # Create config file
            config_file = Path(tmpdir) / 'config.toml'
            config_content = f"""\
input_path = "{input_file}"

[[plugins]]
name = "column_multiplier"
module = "cryoflow_plugin_collections.transform.multiplier"
enabled = true

[plugins.options]
column_name = "amount"
multiplier = 2

[[plugins]]
name = "parquet_writer"
module = "cryoflow_plugin_collections.output.parquet_writer"
enabled = true

[plugins.options]
output_path = "{tmpdir}/output.parquet"
"""
            config_file.write_text(config_content)

            # Run check command
            runner = CliRunner()
            result = runner.invoke(app, ['check', '-c', str(config_file)])

            # Verify success
            assert result.exit_code == 0
            assert '[SUCCESS] Validation completed successfully' in result.stdout
            assert 'Output schema:' in result.stdout
            # Verify schema columns are listed
            assert 'amount' in result.stdout
            assert 'item' in result.stdout

    def test_check_command_missing_config(self) -> None:
        """Test check command with missing config file."""
        runner = CliRunner()
        result = runner.invoke(
            app, ['check', '-c', '/nonexistent/path/config.toml']
        )

        # Verify error
        assert result.exit_code == 2  # Typer validation error

    def test_check_command_with_verbose(self) -> None:
        """Test check command with verbose flag."""
        from cryoflow_plugin_collections.output.parquet_writer import ParquetWriterPlugin
        from cryoflow_plugin_collections.transform.multiplier import ColumnMultiplierPlugin

        with TemporaryDirectory() as tmpdir:
            # Create input file
            input_file = Path(tmpdir) / 'input.parquet'
            input_df = pl.DataFrame({'value': [1, 2, 3]})
            input_df.write_parquet(input_file)

            # Create config file
            config_file = Path(tmpdir) / 'config.toml'
            config_content = f"""\
input_path = "{input_file}"

[[plugins]]
name = "column_multiplier"
module = "cryoflow_plugin_collections.transform.multiplier"
enabled = true

[plugins.options]
column_name = "value"
multiplier = 2

[[plugins]]
name = "parquet_writer"
module = "cryoflow_plugin_collections.output.parquet_writer"
enabled = true

[plugins.options]
output_path = "{tmpdir}/output.parquet"
"""
            config_file.write_text(config_content)

            # Run check command with verbose flag
            runner = CliRunner()
            result = runner.invoke(
                app, ['check', '-c', str(config_file), '-v']
            )

            # Verify success and verbose output
            assert result.exit_code == 0
            assert '[SUCCESS] Validation completed successfully' in result.stdout
            # Verbose output should contain INFO/DEBUG logs
            assert 'Validating' in result.stdout or '[SUCCESS]' in result.stdout

    def test_check_command_transform_validation_fails(self) -> None:
        """Test check command when transform validation fails."""
        with TemporaryDirectory() as tmpdir:
            # Create input file
            input_file = Path(tmpdir) / 'input.parquet'
            input_df = pl.DataFrame({'value': [1, 2, 3]})
            input_df.write_parquet(input_file)

            # Create config file with invalid column name
            config_file = Path(tmpdir) / 'config.toml'
            config_content = f"""\
input_path = "{input_file}"

[[plugins]]
name = "column_multiplier"
module = "cryoflow_plugin_collections.transform.multiplier"
enabled = true

[plugins.options]
column_name = "nonexistent_column"
multiplier = 2

[[plugins]]
name = "parquet_writer"
module = "cryoflow_plugin_collections.output.parquet_writer"
enabled = true

[plugins.options]
output_path = "{tmpdir}/output.parquet"
"""
            config_file.write_text(config_content)

            # Run check command
            runner = CliRunner()
            result = runner.invoke(app, ['check', '-c', str(config_file)])

            # Verify error
            assert result.exit_code == 1
            assert '[ERROR]' in result.stdout or '[ERROR]' in result.stderr
            assert 'Validation failed' in result.stdout or 'Validation failed' in result.stderr
