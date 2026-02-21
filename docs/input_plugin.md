# InputPlugin Guide

## Table of Contents

- [1. Introduction](#1-introduction)
- [2. What is InputPlugin](#2-what-is-inputplugin)
  - [2.1 Differences from Other Plugin Types](#21-differences-from-other-plugin-types)
  - [2.2 Label Feature and Multi-Stream Processing](#22-label-feature-and-multi-stream-processing)
- [3. Interface](#3-interface)
  - [3.1 execute Method](#31-execute-method)
  - [3.2 dry_run Method](#32-dry_run-method)
- [4. Built-in Plugins](#4-built-in-plugins)
  - [4.1 IpcScanPlugin](#41-ipcscanplugin)
  - [4.2 ParquetScanPlugin](#42-parquetscanplugin)
- [5. Implementing a Custom InputPlugin](#5-implementing-a-custom-inputplugin)
  - [5.1 Basic Implementation](#51-basic-implementation)
  - [5.2 Example: CSV File Reader Plugin](#52-example-csv-file-reader-plugin)
- [6. Using in Configuration Files](#6-using-in-configuration-files)
  - [6.1 Basic Configuration Example](#61-basic-configuration-example)
  - [6.2 Multi-Stream Configuration Example](#62-multi-stream-configuration-example)
- [7. Writing Tests](#7-writing-tests)
- [8. Reference](#8-reference)

---

## 1. Introduction

This guide explains the `InputPlugin` concept in Cryoflow.

In earlier versions, the input data path was specified directly via the `input_path` key in the configuration file. The `InputPlugin` now takes on this responsibility, making **data loading pluggable and interchangeable**.

---

## 2. What is InputPlugin

`InputPlugin` is the plugin type responsible for loading data. It is **swappable depending on the data source type**, such as file reading or database queries.

Position in the pipeline:

```
InputPlugin → TransformPlugin(s) → OutputPlugin(s)
    ↓
Produces data (FrameData)
    ↓
Transform / process
    ↓
Output
```

### 2.1 Differences from Other Plugin Types

| Plugin Type | execute Arguments | execute Return Value | Role |
|---|---|---|---|
| **InputPlugin** | none | `Result[FrameData, Exception]` | Generates / loads data |
| TransformPlugin | `df: FrameData` | `Result[FrameData, Exception]` | Transforms data |
| OutputPlugin | `df: FrameData` | `Result[None, Exception]` | Outputs data |

The InputPlugin's `execute` takes **no arguments** — it generates data from a source rather than receiving it from upstream.

The `dry_run` signatures also differ:

| Plugin Type | dry_run Arguments | dry_run Return Value |
|---|---|---|
| **InputPlugin** | none | `Result[dict[str, pl.DataType], Exception]` |
| TransformPlugin | `schema: dict[str, pl.DataType]` | `Result[dict[str, pl.DataType], Exception]` |
| OutputPlugin | `schema: dict[str, pl.DataType]` | `Result[dict[str, pl.DataType], Exception]` |

The InputPlugin's `dry_run` returns only the schema without loading actual data.

### 2.2 Label Feature and Multi-Stream Processing

All plugins have a `label` (default: `'default'`).

The `label` is used to **identify multiple input data streams**. Plugins with the same label are linked together:

```
InputPlugin(label='sales')  →  data_map['sales']  →  TransformPlugin(label='sales')
InputPlugin(label='master') →  data_map['master'] →  TransformPlugin(label='master')
```

For a single data stream, omit `label` or use `'default'`.

---

## 3. Interface

```python
from abc import abstractmethod
import polars as pl
from returns.result import Result
from cryoflow_plugin_collections.libs.core import InputPlugin, FrameData

class InputPlugin(BasePlugin):
    @abstractmethod
    def execute(self) -> Result[FrameData, Exception]:
        """Load and return data as FrameData."""

    @abstractmethod
    def dry_run(self) -> Result[dict[str, pl.DataType], Exception]:
        """Return the schema without loading actual data."""
```

### 3.1 execute Method

`execute` is called with no arguments and loads data from the data source.

**Return value**:
- `Success(LazyFrame)` or `Success(DataFrame)`: loading succeeded
- `Failure(Exception)`: loading failed

**Notes**:
- Prefer using lazy evaluation APIs like `pl.scan_*` to return a `LazyFrame`
- Ideally, leave calling `collect()` to the OutputPlugin

### 3.2 dry_run Method

`dry_run` returns the output schema (a mapping of column names to data types) without loading actual data.

**Return value**:
- `Success(dict[str, pl.DataType])`: schema retrieval succeeded
- `Failure(Exception)`: schema retrieval failed

**Purpose**: Used during pre-validation with the `cryoflow check` command.

---

## 4. Built-in Plugins

The `cryoflow-plugin-collections` package ships with the following InputPlugins.

### 4.1 IpcScanPlugin

A plugin that loads data from Apache Arrow IPC format files.

**Module**: `cryoflow_plugin_collections.input.ipc_scan`

**Options**:

| Option | Type | Required | Description |
|---|---|---|---|
| `input_path` | `str` | Yes | Path to the input IPC file |

**Configuration example**:

```toml
[[input_plugins]]
name = "ipc-input"
module = "cryoflow_plugin_collections.input.ipc_scan"
enabled = true
[input_plugins.options]
input_path = "data/input.arrow"
```

### 4.2 ParquetScanPlugin

A plugin that loads data from Parquet format files.

**Module**: `cryoflow_plugin_collections.input.parquet_scan`

**Options**:

| Option | Type | Required | Description |
|---|---|---|---|
| `input_path` | `str` | Yes | Path to the input Parquet file |

**Configuration example**:

```toml
[[input_plugins]]
name = "parquet-input"
module = "cryoflow_plugin_collections.input.parquet_scan"
enabled = true
[input_plugins.options]
input_path = "data/input.parquet"
```

---

## 5. Implementing a Custom InputPlugin

### 5.1 Basic Implementation

```python
from cryoflow_plugin_collections.libs.polars import pl
from cryoflow_plugin_collections.libs.returns import Result, Success, Failure
from cryoflow_plugin_collections.libs.core import InputPlugin, FrameData


class MyInputPlugin(InputPlugin):
    def name(self) -> str:
        """Plugin identifier name (used in logs and error messages)."""
        return 'my_input'

    def execute(self) -> Result[FrameData, Exception]:
        """Load data (no arguments)."""
        try:
            # Retrieve options from self.options
            input_path_opt = self.options.get('input_path')
            if input_path_opt is None:
                return Failure(ValueError("Option 'input_path' is required"))

            # Use self.resolve_path() to resolve relative paths against the config dir
            input_path = self.resolve_path(input_path_opt)
            if not input_path.exists():
                return Failure(FileNotFoundError(f'Input file not found: {input_path}'))

            # Return a LazyFrame (do not call collect())
            return Success(pl.scan_parquet(input_path))
        except Exception as e:
            return Failure(e)

    def dry_run(self) -> Result[dict[str, pl.DataType], Exception]:
        """Return schema without loading actual data."""
        try:
            input_path_opt = self.options.get('input_path')
            if input_path_opt is None:
                return Failure(ValueError("Option 'input_path' is required"))

            input_path = self.resolve_path(input_path_opt)
            if not input_path.exists():
                return Failure(FileNotFoundError(f'Input file not found: {input_path}'))

            # Retrieve schema only (no actual data loaded)
            return Success(dict(pl.scan_parquet(input_path).collect_schema()))
        except Exception as e:
            return Failure(e)
```

### 5.2 Example: CSV File Reader Plugin

A complete example of an InputPlugin that reads CSV files.

```python
"""CSV file input plugin."""

from cryoflow_plugin_collections.libs.polars import pl
from cryoflow_plugin_collections.libs.returns import Failure, Result, Success
from cryoflow_plugin_collections.libs.core import FrameData, InputPlugin


class CsvScanPlugin(InputPlugin):
    """Load data from a CSV file.

    Options:
        input_path (str): Path to the input CSV file.
        separator (str): Field delimiter (default: ',').
        has_header (bool): Whether the file has a header row (default: True).
    """

    def name(self) -> str:
        return 'csv_scan'

    def execute(self) -> Result[FrameData, Exception]:
        """Load data from a CSV file.

        Returns:
            Result containing LazyFrame on success or Exception on failure.
        """
        try:
            input_path_opt = self.options.get('input_path')
            if input_path_opt is None:
                return Failure(ValueError("Option 'input_path' is required"))

            input_path = self.resolve_path(input_path_opt)
            if not input_path.exists():
                return Failure(FileNotFoundError(f'Input file not found: {input_path}'))

            separator = self.options.get('separator', ',')
            has_header = self.options.get('has_header', True)

            return Success(
                pl.scan_csv(
                    input_path,
                    separator=separator,
                    has_header=has_header,
                )
            )
        except Exception as e:
            return Failure(e)

    def dry_run(self) -> Result[dict[str, pl.DataType], Exception]:
        """Return the schema without loading actual data.

        Returns:
            Result containing schema dict on success or Exception on failure.
        """
        try:
            input_path_opt = self.options.get('input_path')
            if input_path_opt is None:
                return Failure(ValueError("Option 'input_path' is required"))

            input_path = self.resolve_path(input_path_opt)
            if not input_path.exists():
                return Failure(FileNotFoundError(f'Input file not found: {input_path}'))

            separator = self.options.get('separator', ',')
            has_header = self.options.get('has_header', True)

            schema = pl.scan_csv(
                input_path,
                separator=separator,
                has_header=has_header,
            ).collect_schema()
            return Success(dict(schema))
        except Exception as e:
            return Failure(e)
```

---

## 6. Using in Configuration Files

InputPlugins are configured under `[[input_plugins]]` in `config.toml`.

### 6.1 Basic Configuration Example

```toml
# Using the built-in Parquet reader plugin
[[input_plugins]]
name = "parquet-input"
module = "cryoflow_plugin_collections.input.parquet_scan"
enabled = true
[input_plugins.options]
input_path = "data/input.parquet"

[[transform_plugins]]
name = "my-transform"
module = "my_plugins.transform.my_transform"
enabled = true
[transform_plugins.options]
column_name = "value"

[[output_plugins]]
name = "parquet-output"
module = "cryoflow_plugin_collections.output.parquet_write"
enabled = true
[output_plugins.options]
output_path = "data/output.parquet"
```

### 6.2 Multi-Stream Configuration Example

Using `label` to work with multiple input data streams.

```toml
# Load sales data
[[input_plugins]]
name = "sales-input"
module = "cryoflow_plugin_collections.input.parquet_scan"
enabled = true
label = "sales"
[input_plugins.options]
input_path = "data/sales.parquet"

# Load master data
[[input_plugins]]
name = "master-input"
module = "cryoflow_plugin_collections.input.parquet_scan"
enabled = true
label = "master"
[input_plugins.options]
input_path = "data/master.parquet"

# Transform sales data (label = "sales")
[[transform_plugins]]
name = "sales-filter"
module = "my_plugins.transform.filter"
enabled = true
label = "sales"
[transform_plugins.options]
column_name = "amount"
threshold = 1000

# Output sales data
[[output_plugins]]
name = "sales-output"
module = "cryoflow_plugin_collections.output.parquet_write"
enabled = true
label = "sales"
[output_plugins.options]
output_path = "data/filtered_sales.parquet"
```

**Label associations**:

```
InputPlugin(label='sales')  →  TransformPlugin(label='sales')  →  OutputPlugin(label='sales')
InputPlugin(label='master') →  (no transform)                  →  (no output)
```

Data streams with no corresponding TransformPlugin or OutputPlugin for their label are simply not processed.

---

## 7. Writing Tests

Tests for InputPlugin should verify:

- `execute()` returns `Success(LazyFrame)` correctly
- `dry_run()` returns the correct schema
- `Failure` is returned when required options are missing
- `Failure` is returned when the file does not exist

```python
from pathlib import Path
import pytest
import polars as pl
from returns.result import Success, Failure

from my_plugins.input.csv_scan import CsvScanPlugin


class TestCsvScanPlugin:
    """Test suite for CsvScanPlugin."""

    @pytest.fixture
    def sample_csv(self, tmp_path: Path) -> Path:
        """Create a temporary CSV file for testing."""
        csv_path = tmp_path / 'test.csv'
        csv_path.write_text("id,value\n1,100\n2,200\n3,300\n")
        return csv_path

    @pytest.fixture
    def plugin(self, sample_csv: Path) -> CsvScanPlugin:
        """Create a plugin instance."""
        return CsvScanPlugin(
            options={'input_path': str(sample_csv)},
            config_dir=sample_csv.parent,
        )

    def test_name(self, plugin: CsvScanPlugin):
        """Plugin name should be correct."""
        assert plugin.name() == 'csv_scan'

    def test_execute_success(self, plugin: CsvScanPlugin):
        """Successful loading should return the correct data."""
        result = plugin.execute()

        assert isinstance(result, Success)
        df = result.unwrap().collect()
        assert df.shape == (3, 2)
        assert df['id'].to_list() == [1, 2, 3]
        assert df['value'].to_list() == [100, 200, 300]

    def test_execute_returns_lazyframe(self, plugin: CsvScanPlugin):
        """execute should return a LazyFrame."""
        result = plugin.execute()

        assert isinstance(result, Success)
        assert isinstance(result.unwrap(), pl.LazyFrame)

    def test_execute_missing_input_path(self, sample_csv: Path):
        """Missing required option input_path should return Failure."""
        plugin = CsvScanPlugin(
            options={},
            config_dir=sample_csv.parent,
        )
        result = plugin.execute()

        assert isinstance(result, Failure)
        assert "'input_path' is required" in str(result.failure())

    def test_execute_file_not_found(self, tmp_path: Path):
        """Nonexistent file should return Failure."""
        plugin = CsvScanPlugin(
            options={'input_path': 'nonexistent.csv'},
            config_dir=tmp_path,
        )
        result = plugin.execute()

        assert isinstance(result, Failure)
        assert isinstance(result.failure(), FileNotFoundError)

    def test_dry_run_success(self, plugin: CsvScanPlugin):
        """dry_run should return the correct schema."""
        result = plugin.dry_run()

        assert isinstance(result, Success)
        schema = result.unwrap()
        assert 'id' in schema
        assert 'value' in schema

    def test_dry_run_missing_input_path(self, sample_csv: Path):
        """Missing required option input_path should return Failure."""
        plugin = CsvScanPlugin(
            options={},
            config_dir=sample_csv.parent,
        )
        result = plugin.dry_run()

        assert isinstance(result, Failure)
        assert "'input_path' is required" in str(result.failure())
```

---

## 8. Reference

### InputPlugin Class API

```python
class InputPlugin(BasePlugin):
    def execute(self) -> Result[FrameData, Exception]:
        """Load and return data as FrameData.

        Takes no arguments. Generates data directly from the data source.

        Returns:
            Success: Loaded data frame (LazyFrame preferred)
            Failure: Loading error
        """

    def dry_run(self) -> Result[dict[str, pl.DataType], Exception]:
        """Return schema without loading actual data.

        Takes no arguments. Reads only file metadata.

        Returns:
            Success: Schema (column name → DataType mapping)
            Failure: Schema retrieval error
        """
```

### Methods Inherited from BasePlugin

```python
def resolve_path(self, path: str | Path) -> Path:
    """Resolve a path relative to the config file directory.

    Absolute paths are returned as-is.
    Relative paths are resolved against the config file directory (self._config_dir).

    Example:
        >>> # When config.toml is at /project/config/config.toml
        >>> plugin.resolve_path("data/input.parquet")
        PosixPath('/project/config/data/input.parquet')
    """
```

### Import Paths

```python
# Base class and type definitions
from cryoflow_plugin_collections.libs.core import InputPlugin, FrameData

# Polars
from cryoflow_plugin_collections.libs.polars import pl

# Result types
from cryoflow_plugin_collections.libs.returns import Result, Success, Failure
```

### Built-in Plugin Module Paths

| Plugin | Module |
|---|---|
| IPC (Arrow) input | `cryoflow_plugin_collections.input.ipc_scan` |
| Parquet input | `cryoflow_plugin_collections.input.parquet_scan` |

---

### Related Documentation

- [Plugin Development Guide](plugin_development.md): How to implement TransformPlugin and OutputPlugin
- [Specification](spec.md): System-wide architecture and design
