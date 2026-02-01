# cryoflow

A plugin-driven columnar data processing CLI tool built on Polars LazyFrame.

Processes Apache Arrow (IPC/Parquet) format data through a chain of user-defined plugins for data transformation, validation, and output.

## Technology Stack

| Category | Library/Technology | Purpose |
| --- | --- | --- |
| Core | Polars | Data processing engine (LazyFrame-based) |
| CLI | Typer | CLI interface and command definitions |
| Plugin | pluggy + importlib | Plugin mechanism, hook management, dynamic loading |
| Config | Pydantic + TOML | Configuration definition and validation |
| Path | xdg-base-dirs | XDG-compliant configuration path resolution |
| Error | returns | Error handling via Result Monad and railway-oriented programming |
| Base | ABC (Standard Lib) | Plugin interface definitions |

## Data Flow

1. **Config Load**: Load `XDG_CONFIG_HOME/cryoflow/config.toml` and validate with Pydantic
2. **Plugin Discovery**: Load specified modules via `importlib` and register with `pluggy` based on configuration
3. **Pipeline Construction**: Convert source (Parquet/IPC) to LazyFrame via `pl.scan_*`, execute `TransformPlugin` hooks sequentially to build the computation graph
4. **Execution / Output**: Execute `OutputPlugin` hooks. This is where `collect()` or `sink_*()` is first called and processing actually runs

## Plugin System

Plugins are created by inheriting base classes defined via ABC.

- **TransformPlugin**: Plugin for data transformation. Implements `execute(df) -> Result[FrameData, Exception]`
- **OutputPlugin**: Plugin for data output. Implements `execute(df) -> Result[None, Exception]`

All plugins have a `dry_run` method that enables schema validation without processing actual data.

## Error Handling

Uses the `returns` library for railway-oriented programming with the `Result` type.

- Data passed between plugins is wrapped in `Result[FrameData, Exception]`
- Pipeline control uses `flow` / `bind` and immediately halts processing when `Failure` occurs

## CLI Commands

### run command

Executes the data processing pipeline.

```bash
# Use default configuration file
cryoflow run

# Specify custom configuration file
cryoflow run -c path/to/config.toml

# Output detailed logs
cryoflow run -c path/to/config.toml -v
```

### check command

Validates pipeline configuration and schema without processing actual data.

```bash
# Verify configuration validity and schema
cryoflow check -c path/to/config.toml

# Verify with detailed logs
cryoflow check -c path/to/config.toml -v
```

**Use cases for check command**:

- Syntax validation of configuration file
- Verify plugin loading capability
- Schema validation (confirm transformed column types)
- Pre-flight validation before actual execution

## Documentation

- [Specification](docs/spec.md)
- [Implementation Plan](docs/implements_step_plan.md)
- [Progress](docs/progress.md)
