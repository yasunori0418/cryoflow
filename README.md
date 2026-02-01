# cryoflow

A plugin-driven columnar data processing CLI tool built on Polars LazyFrame.

**cryoflow** is a powerful tool for processing Apache Arrow (IPC/Parquet) format data through a customizable chain of plugins. It enables you to perform complex data transformations, validations, and output operations with a simple configuration file.

## Features

- 🔌 **Plugin-Driven Architecture**: Extend functionality by writing custom plugins
- ⚡ **Lazy Evaluation**: Powered by Polars LazyFrame for efficient data processing
- 📋 **Configuration-Based**: Define your data pipeline in TOML configuration files
- ✅ **Dry-Run Mode**: Validate your pipeline configuration and schema before processing
- 🛡️ **Robust Error Handling**: Railway-oriented programming with Result types
- 🔄 **Streaming Support**: Process both Parquet and Apache Arrow IPC formats
- 🎯 **Type-Safe**: End-to-end type safety from data loading to output

## Prerequisites

- Python 3.14 or higher
- pip or [uv](https://astral.sh/uv/) (optional, for faster installation)

## Installation

### Using pip

```bash
pip install cryoflow
```

### Using uv (recommended)

```bash
uv pip install cryoflow
```

### Using Nix

If you have Nix installed, you can run cryoflow directly:

```bash
nix run github:yasunori0418/cryoflow -- --help
```

Or add cryoflow to your NixOS configuration or flake.nix:

```nix
inputs = {
  cryoflow.url = "github:yasunori0418/cryoflow";
};
```

### From Source

```bash
git clone https://github.com/yasunori0418/cryoflow
cd cryoflow
uv sync  # or pip install -e .
```

### Development with Nix Flake and direnv

For development purposes, you can use either direnv or nix CLI:

#### Using direnv (recommended)

```bash
# Copy the example configuration
cp example.envrc .envrc

# Allow direnv to load the configuration
direnv allow
```

This automatically loads the development environment with Nix, including uv, ruff, and pyright tools. When you enter the directory, direnv automatically activates the environment defined in `dev/flake.nix`.

#### Using Nix CLI

```bash
# Enter the development environment from dev/flake.nix
nix develop ./dev
```

## Quick Start

### 1. Create a Configuration File

Create a `config.toml` file:

```toml
input_path = "data/input.parquet"
output_target = "data/output.parquet"

[[plugins]]
name = "column-multiplier"
module = "cryoflow_sample_plugin.transform"
enabled = true
[plugins.options]
column_name = "amount"
multiplier = 2

[[plugins]]
name = "parquet-writer"
module = "cryoflow_sample_plugin.output"
enabled = true
[plugins.options]
output_path = "data/output.parquet"
```

### 2. Run the Pipeline

```bash
cryoflow run -c config.toml
```

### 3. Validate Configuration

Before running, validate your configuration:

```bash
cryoflow check -c config.toml
```

## Usage

### CLI Commands

#### `run` - Execute Data Processing Pipeline

Executes the complete data processing pipeline as defined in the configuration file.

```bash
# Use default configuration file (searches XDG_CONFIG_HOME/cryoflow/config.toml)
cryoflow run

# Specify custom configuration file
cryoflow run -c path/to/config.toml

# Output detailed logs for debugging
cryoflow run -c config.toml -v
```

#### `check` - Validate Configuration & Schema

Validates pipeline configuration and schema without processing actual data. This is useful for pre-flight checks.

```bash
# Verify configuration validity
cryoflow check -c config.toml

# Verify with detailed logs
cryoflow check -c config.toml -v
```

**Use cases for check command**:

- Validate TOML syntax of configuration file
- Verify that all required plugins can be loaded
- Validate schema transformations (confirm transformed column types)
- Pre-flight validation before running large data processing jobs

### Configuration File

The configuration file uses TOML format and defines:

- **input_path**: Path to input Parquet or IPC file
- **output_target**: Target output specification (plugin-dependent)
- **plugins**: Array of plugin configurations

Each plugin entry specifies:

- **name**: Plugin identifier
- **module**: Python module path to load the plugin from
- **enabled**: Whether the plugin should be executed (true/false)
- **options**: Plugin-specific configuration options

### Example Configuration

```toml
# Input/Output specification
input_path = "examples/data/sample_sales.parquet"
output_target = "examples/data/output.parquet"

# First plugin: Transform data
[[plugins]]
name = "column-multiplier"
module = "cryoflow_sample_plugin.transform"
enabled = true
[plugins.options]
column_name = "total_amount"
multiplier = 2

# Second plugin: Output result
[[plugins]]
name = "parquet-writer"
module = "cryoflow_sample_plugin.output"
enabled = true
[plugins.options]
output_path = "examples/data/output.parquet"
```

### Configuration File Locations

cryoflow searches for configuration files in the following order:

1. Explicitly specified path via `-c` option
2. `$XDG_CONFIG_HOME/cryoflow/config.toml` (typically `~/.config/cryoflow/config.toml`)
3. Default examples configuration (if available)

## Plugin System

Plugins are the core extension mechanism in cryoflow. There are two types of plugins:

### TransformPlugin

Transforms data in the pipeline. Receives a DataFrame/LazyFrame and returns the transformed result.

```python
class MyTransformPlugin(TransformPlugin):
    def execute(self, df: FrameData) -> Result[FrameData, Exception]:
        # Your transformation logic
        return Success(df.with_columns(...))

    def dry_run(self, schema: dict) -> Result[dict, Exception]:
        # Validate transformation with schema
        return Success(new_schema)
```

### OutputPlugin

Outputs data to storage. Receives the final DataFrame/LazyFrame and handles output operations.

```python
class MyOutputPlugin(OutputPlugin):
    def execute(self, df: FrameData) -> Result[None, Exception]:
        # Your output logic
        df.sink_parquet("output.parquet")
        return Success(None)

    def dry_run(self, schema: dict) -> Result[None, Exception]:
        # Validate output capability
        return Success(None)
```

All plugins have a `dry_run` method that enables schema validation without processing actual data.

## Error Handling

cryoflow uses the `returns` library for robust error handling through railway-oriented programming with the `Result` type.

- Data passed between plugins is wrapped in `Result[FrameData, Exception]`
- Pipeline control uses `flow`/`bind` combinators and immediately halts processing when a `Failure` occurs
- No silent failures - all errors are explicitly handled

## Data Flow Architecture

```
Config Load
    ↓
Plugin Discovery
    ↓
Pipeline Construction
    ↓
Execution / Output
```

1. **Config Load**: Load and validate configuration from TOML file using Pydantic
2. **Plugin Discovery**: Load specified modules via `importlib` and register with `pluggy`
3. **Pipeline Construction**: Convert source data to LazyFrame, execute `TransformPlugin` hooks to build the computation graph
4. **Execution / Output**: Execute `OutputPlugin` hooks where `collect()` or `sink_*()` is called and processing actually runs

## Technology Stack

| Category | Library/Technology | Purpose |
| --- | --- | --- |
| Core | Polars | Columnar data processing engine (LazyFrame-based) |
| CLI | Typer | Modern CLI framework and command definitions |
| Plugin | pluggy + importlib | Plugin mechanism, hook management, dynamic loading |
| Config | Pydantic + TOML | Type-safe configuration definition and validation |
| Path | xdg-base-dirs | XDG Base Directory specification compliance |
| Error | returns | Functional error handling via Result Monad |
| Base | ABC (Standard Lib) | Plugin interface definitions |

## Examples

Sample data and configuration files are provided in the `examples/` directory:

```bash
# Run the sample pipeline
cryoflow run -c examples/config.toml

# Check the sample configuration
cryoflow check -c examples/config.toml
```

The examples directory includes:

- `config.toml`: Sample pipeline configuration
- `data/sample_sales.parquet`: Sample sales data (Parquet format)
- `data/sample_sales.ipc`: Same data in Arrow IPC format
- `data/sensor_readings.parquet`: Sensor data example

## Documentation

For detailed information, see:

- [Specification](docs/spec.md) - Complete API specification and interface design
- [Implementation Plan](docs/implements_step_plan.md) - Technical implementation details
- [Progress](docs/progress.md) - Project development progress

English documentation is available as `docs/{filename}.md`.
日本語ドキュメントは `docs/{filename}_ja.md` をご参照ください。

## Troubleshooting

### Configuration File Not Found

**Error**: `Configuration file not found`

**Solution**:
- Check that the file path is correct
- Use `-c` option to specify the configuration file explicitly
- Ensure `~/.config/cryoflow/config.toml` exists if using default location

### Plugin Not Found

**Error**: `Module not found: cryoflow_sample_plugin`

**Solution**:
- Install required plugins: `pip install cryoflow-sample-plugin`
- Verify the module path in the configuration file

### Schema Validation Error

**Error**: `Schema validation failed`

**Solution**:
- Run `cryoflow check -c config.toml -v` to see detailed validation logs
- Verify column names and types match your input data
- Check plugin options are correct

### For More Help

- Check example configurations in `examples/` directory
- Run with `-v` flag for verbose logging
- See documentation in `docs/` directory

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues, questions, or suggestions, please open an issue on the [GitHub repository](https://github.com/yasunori0418/cryoflow/issues).
