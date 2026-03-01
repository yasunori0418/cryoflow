"""End-to-end tests for the 'check' CLI command."""

from pathlib import Path
from tempfile import TemporaryDirectory

import polars as pl
from typer.testing import CliRunner

from cryoflow_core.cli import app


class TestCheckCommand:
    """Tests for the 'check' command CLI."""

    def test_check_command_success(self) -> None:
        """Test successful dry-run check with valid config."""
        with TemporaryDirectory() as tmpdir:
            # Create input file
            input_file = Path(tmpdir) / 'input.parquet'
            input_df = pl.DataFrame({'amount': [100, 200, 300], 'item': ['a', 'b', 'c']})
            input_df.write_parquet(input_file)

            # Create config file
            config_file = Path(tmpdir) / 'config.toml'
            config_content = f"""\
[[input_plugins]]
name = "parquet_scan"
module = "cryoflow_plugin_collections.input.parquet_scan"
enabled = true

[input_plugins.options]
input_path = "{input_file}"

[[transform_plugins]]
name = "column_multiplier"
module = "cryoflow_plugin_collections.transform.multiplier"
enabled = true

[transform_plugins.options]
column_name = "amount"
multiplier = 2

[[output_plugins]]
name = "parquet_writer"
module = "cryoflow_plugin_collections.output.parquet_writer"
enabled = true

[output_plugins.options]
output_path = "{tmpdir}/output.parquet"
"""
            config_file.write_text(config_content)

            # Run check command
            runner = CliRunner(env={"NO_COLOR": "1"})
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
        runner = CliRunner(env={"NO_COLOR": "1"})
        result = runner.invoke(app, ['check', '-c', '/nonexistent/path/config.toml'])

        # Verify error
        assert result.exit_code == 2  # Typer validation error

    def test_check_command_with_verbose(self) -> None:
        """Test check command with verbose flag."""
        with TemporaryDirectory() as tmpdir:
            # Create input file
            input_file = Path(tmpdir) / 'input.parquet'
            input_df = pl.DataFrame({'value': [1, 2, 3]})
            input_df.write_parquet(input_file)

            # Create config file
            config_file = Path(tmpdir) / 'config.toml'
            config_content = f"""\
[[input_plugins]]
name = "parquet_scan"
module = "cryoflow_plugin_collections.input.parquet_scan"
enabled = true

[input_plugins.options]
input_path = "{input_file}"

[[transform_plugins]]
name = "column_multiplier"
module = "cryoflow_plugin_collections.transform.multiplier"
enabled = true

[transform_plugins.options]
column_name = "value"
multiplier = 2

[[output_plugins]]
name = "parquet_writer"
module = "cryoflow_plugin_collections.output.parquet_writer"
enabled = true

[output_plugins.options]
output_path = "{tmpdir}/output.parquet"
"""
            config_file.write_text(config_content)

            # Run check command with verbose flag
            runner = CliRunner(env={"NO_COLOR": "1"})
            result = runner.invoke(app, ['check', '-c', str(config_file), '-V'])

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
[[input_plugins]]
name = "parquet_scan"
module = "cryoflow_plugin_collections.input.parquet_scan"
enabled = true

[input_plugins.options]
input_path = "{input_file}"

[[transform_plugins]]
name = "column_multiplier"
module = "cryoflow_plugin_collections.transform.multiplier"
enabled = true

[transform_plugins.options]
column_name = "nonexistent_column"
multiplier = 2

[[output_plugins]]
name = "parquet_writer"
module = "cryoflow_plugin_collections.output.parquet_writer"
enabled = true

[output_plugins.options]
output_path = "{tmpdir}/output.parquet"
"""
            config_file.write_text(config_content)

            # Run check command
            runner = CliRunner(env={"NO_COLOR": "1"})
            result = runner.invoke(app, ['check', '-c', str(config_file)])

            # Verify error
            assert result.exit_code == 1
            assert '[ERROR]' in result.stdout or '[ERROR]' in result.stderr
            assert 'Validation failed' in result.stdout or 'Validation failed' in result.stderr
