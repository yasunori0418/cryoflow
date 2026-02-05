# CLITool "cryoflow" Specification

## 1. Overview

A plugin-driven columnar data processing CLI tool built on Polars LazyFrame.
Processes Apache Arrow (IPC/Parquet) format data through a chain of user-defined plugins for data transformation, validation, and output.

## 2. Architecture

### 2.1 Technology Stack

| Category | Library/Technology | Purpose |
| --- | --- | --- |
| **Core** | **Polars** | Data processing engine (LazyFrame-based) |
| **CLI** | **Typer** | CLI interface and command definitions |
| **Plugin** | **pluggy** + **importlib** | Plugin mechanism, hook management, dynamic loading |
| **Config** | **Pydantic** + **TOML** | Configuration definition and validation |
| **Path** | **xdg-base-dirs** | XDG-compliant configuration path resolution |
| **Error** | **returns** | Railway-oriented programming style error handling via Result Monad |
| **Base** | **ABC** (Standard Lib) | Plugin interface definitions |

### 2.2 Data Flow

1. **Config Load**: Load `XDG_CONFIG_HOME/cryoflow/config.toml` and validate with Pydantic.
2. **Plugin Discovery**: Load specified modules via `importlib` and register with `pluggy` based on configuration.
3. **Pipeline Construction**:
   - Convert source (Parquet/IPC) to LazyFrame via `pl.scan_*`.
   - Execute `TransformPlugin` hooks sequentially to build the computation graph (LazyFrame).

4. **Execution / Output**:
   - Execute `OutputPlugin` hooks. This is where `collect()` or `sink_*()` is first called and processing actually runs.

---

## 3. Interface Design

### 3.1 Data Models (Pydantic)

```python
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

class PluginConfig(BaseModel):
    name: str
    module: str  # Path to load with importlib
    enabled: bool = True
    options: dict[str, Any] = Field(default_factory=dict)  # Plugin-specific configuration

class CryoflowConfig(BaseModel):
    input_path: Path  # Use Path instead of FilePath to avoid enforcing file existence at config load time
    output_target: str
    plugins: list[PluginConfig]
```

> **Implementation Notes**:
> - `GlobalConfig` renamed to `CryoflowConfig` (clearer naming)
> - `input_path` type changed from `FilePath` to `Path` (don't enforce file existence at config load time)
> - Uses Python 3.14 built-in types (`list`, `dict`) instead of deprecated `typing.List`, `typing.Dict`

### 3.2 Plugin Base Classes (ABC)

While `pluggy` can handle function-based hooks, we use class-based plugins to enforce the contract via ABC and to mandate the `dry_run` method.

```python
from abc import ABC, abstractmethod
from typing import Any

import polars as pl
from returns.result import Result

# Type alias for data
FrameData = pl.LazyFrame | pl.DataFrame

class BasePlugin(ABC):
    """Base class for all plugins"""
    def __init__(self, options: dict[str, Any]):
        self.options = options

    @abstractmethod
    def name(self) -> str:
        """Plugin identification name"""
        pass

    @abstractmethod
    def dry_run(self, schema: dict[str, pl.DataType]) -> Result[dict[str, pl.DataType], Exception]:
        """Accept schema only and return predicted output schema (or error)"""
        pass

class TransformPlugin(BasePlugin):
    """Data transformation plugin"""
    @abstractmethod
    def execute(self, df: FrameData) -> Result[FrameData, Exception]:
        pass

class OutputPlugin(BasePlugin):
    """Output plugin"""
    @abstractmethod
    def execute(self, df: FrameData) -> Result[None, Exception]:
        pass
```

### 3.3 Hook Specification (pluggy hookspec)

```python
import pluggy

hookspec = pluggy.HookspecMarker("cryoflow")

class CryoflowSpecs:
    @hookspec
    def register_transform_plugins(self) -> list[TransformPlugin]:
        """Return instances of transformation plugins"""

    @hookspec
    def register_output_plugins(self) -> list[OutputPlugin]:
        """Return instances of output plugins"""
```

---

## 4. Error Handling Guidelines (returns)

- Use exceptions (`try-except`) only at the lowest level library boundaries (e.g., Polars calls).
- Wrap data passed between plugins in `Result[FrameData, Exception]`.
- In pipeline control, use `flow` or `bind` to immediately halt processing when any `Failure` is returned and pass it to CLI error output.

```python
# Conceptual example
result = (
    load_data(path)
    .bind(plugin_a.execute)
    .bind(plugin_b.execute)
    .bind(output_plugin.execute)
)

if isinstance(result, Failure):
    console.print(f"[red]Error:[/red] {result.failure()}")
    raise typer.Exit(code=1)

```

---

## 5. Plugin Implementation Best Practices

### 5.1 Error Handling

The following patterns are recommended for `execute()` and `dry_run()` methods in plugins.

**Pattern 1: Explicitly return Failure with try-except (Recommended)**

```python
from returns.result import Failure, Success

def execute(self, df: FrameData) -> Result[FrameData, Exception]:
    try:
        column_name = self.options['column_name']
        if column_name not in df.columns:
            return Failure(ValueError(f"Column '{column_name}' not found"))
        # ... process ...
        return Success(transformed_df)
    except Exception as e:
        return Failure(e)
```

**Pattern 2: Auto-conversion with @safe decorator**

```python
from returns.result import safe

@safe
def execute(self, df: FrameData) -> FrameData:
    column_name = self.options['column_name']
    if column_name not in df.columns:
        raise ValueError(f"Column '{column_name}' not found")
    # ... process ...
    return transformed_df
```

In both cases, it is important to include specific information in error messages (column names, expected values, actual values).

### 5.2 dry_run Method Implementation

The `dry_run` method inspects the schema only without processing actual data and returns the predicted output schema.

```python
def dry_run(self, schema: dict[str, pl.DataType]) -> Result[dict[str, pl.DataType], Exception]:
    """Validate schema and return predicted output schema"""
    column_name = self.options['column_name']

    # Check column existence
    if column_name not in schema:
        return Failure(ValueError(f"Column '{column_name}' not found in schema"))

    # Check type
    dtype = schema[column_name]
    if not dtype.is_numeric():
        return Failure(ValueError(
            f"Column '{column_name}' has type {dtype}, expected numeric type"
        ))

    # Schema remains unchanged, return as is
    return Success(schema)
```

### 5.3 Resource Management

- Polars `scan_*`/`sink_*` methods automatically close file handles
- When implementing custom OutputPlugin, manage file handles using `with` statements

```python
class CustomOutputPlugin(OutputPlugin):
    def execute(self, df: FrameData) -> Result[None, Exception]:
        try:
            output_path = self.options['output_path']
            with open(output_path, 'w') as f:
                # File processing
                pass
            return Success(None)
        except Exception as e:
            return Failure(e)
```

---

## 6. CLI Commands

### 6.1 run command

Executes the data processing pipeline.

```bash
cryoflow run [-c CONFIG] [-v]
```

**Options**:
- `-c, --config CONFIG`: Configuration file path (if not specified, uses XDG-compliant default path)
- `-v, --verbose`: Output detailed logs (DEBUG level logs are displayed)

**Output Example**:

```
Config loaded: /home/user/.config/cryoflow/config.toml
  input_path:    data/input.parquet
  output_target: data/output.parquet
  plugins:       2 plugin(s)
    - transform_plugin (my.transform) [enabled]
    - output_plugin (my.output) [enabled]
Loaded 2 plugin(s) successfully.

Executing pipeline...
INFO: Executing 1 transformation plugin(s)...
INFO:   [1/1] transform_plugin
[SUCCESS] Pipeline completed successfully
```

### 6.2 check command

Validates pipeline configuration and schema without processing actual data.

```bash
cryoflow check [-c CONFIG] [-v]
```

**Options**:
- `-c, --config CONFIG`: Configuration file path
- `-v, --verbose`: Output detailed logs

**Output Example**:

```
[CHECK] Config loaded: /home/user/.config/cryoflow/config.toml
[CHECK] Loaded 2 plugin(s) successfully.

[CHECK] Running dry-run validation...

[SUCCESS] Validation completed successfully

Output schema:
  order_id: Int64
  customer_id: Int64
  total_amount: Float64
  order_date: Date
```

**Use cases**:

- Configuration file syntax validation
- Verify plugin loading capability
- Schema validation (confirm transformed column types)
- Pre-flight validation before actual execution

**Limitations**:

- Currently supports a single output plugin only. If multiple output plugins are specified in the configuration, an error will be raised.

---

## 7. Implementation Details

### 7.1 Plugin Loader Behavior

The plugin loader (`cryoflow_core/loader.py`) distinguishes between filesystem paths and dotted module paths:

- **Filesystem Path** (e.g., `./plugins/my_plugin.py`): Loaded directly via `importlib.util.spec_from_file_location()`
- **Dotted Module Path** (e.g., `cryoflow_plugin_collections.transform.multiplier`): Loaded via `importlib.import_module()` from installed packages

This allows plugins to be loaded either from local development files or from installed Python packages, providing flexibility in plugin distribution and development workflows.

### 7.2 Schema Extraction from Data Sources

The pipeline automatically detects the format (Parquet/IPC) from the input file extension and extracts the schema:

- **LazyFrame**: Schema is extracted via `schema` property without materializing data
- **DataFrame**: Schema is extracted via the same `schema` property

In both cases, the schema extraction is non-blocking and does not trigger data loading. This enables efficient dry-run validation without I/O overhead.

### 7.3 Result Type and Error Propagation

All plugin methods (`execute`, `dry_run`) return `Result[T, Exception]` types from the `returns` library:

```python
# Transform plugin returns the transformed data
Result[FrameData, Exception]

# Output plugin returns None (None indicates successful output)
Result[None, Exception]
```

Errors are propagated through the pipeline using the `bind()` method, which automatically halts processing on the first `Failure` encountered. This implements railway-oriented programming, ensuring predictable error handling across the entire pipeline.
