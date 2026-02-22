# Cryoflow Plugin Development Guide

## Table of Contents

- [1. Introduction](#1-introduction)
- [2. Plugin Basics](#2-plugin-basics)
  - [2.1 Plugin Types](#21-plugin-types)
  - [2.2 Basic Architecture](#22-basic-architecture)
  - [2.3 Plugin Lifecycle](#23-plugin-lifecycle)
- [3. Development Environment Setup](#3-development-environment-setup)
  - [3.1 Required Packages](#31-required-packages)
  - [3.2 Project Structure](#32-project-structure)
- [4. InputPlugin Implementation Guide](#4-inputplugin-implementation-guide)
  - [4.1 Label Feature and Multi-Stream Processing](#41-label-feature-and-multi-stream-processing)
  - [4.2 Basic Implementation](#42-basic-implementation)
  - [4.3 Example: CSV File Reader Plugin](#43-example-csv-file-reader-plugin)
- [5. TransformPlugin Implementation Guide](#5-transformplugin-implementation-guide)
  - [5.1 Basic Implementation](#51-basic-implementation)
  - [5.2 Example: Column Multiplier Plugin](#52-example-column-multiplier-plugin)
  - [5.3 Leveraging LazyFrame](#53-leveraging-lazyframe)
- [6. OutputPlugin Implementation Guide](#6-outputplugin-implementation-guide)
  - [6.1 Basic Implementation](#61-basic-implementation)
  - [6.2 Example: Parquet Writer Plugin](#62-example-parquet-writer-plugin)
- [7. dry_run Method Implementation](#7-dry_run-method-implementation)
  - [7.1 Purpose and Role](#71-purpose-and-role)
  - [7.2 Implementation Patterns](#72-implementation-patterns)
- [8. Error Handling](#8-error-handling)
  - [8.1 Using Result Type](#81-using-result-type)
  - [8.2 Error Message Best Practices](#82-error-message-best-practices)
  - [8.3 Common Error Patterns](#83-common-error-patterns)
- [9. Writing Tests](#9-writing-tests)
  - [9.1 Basic Test Structure](#91-basic-test-structure)
  - [9.2 Implementation Example](#92-implementation-example)
- [10. Plugin Distribution](#10-plugin-distribution)
  - [10.1 Package Structure](#101-package-structure)
  - [10.2 Dependency Definition](#102-dependency-definition)
  - [10.3 Distribution Methods](#103-distribution-methods)
- [11. Using in Configuration Files](#11-using-in-configuration-files)
- [12. Reference](#12-reference)
  - [12.1 Type Definitions](#121-type-definitions)
  - [12.2 Base Class API](#122-base-class-api)
  - [12.3 Polars Method Reference](#123-polars-method-reference)

---

## 1. Introduction

Cryoflow is a plugin-driven, column-oriented data processing CLI tool built on Polars LazyFrame. This guide explains how to develop custom plugins for Cryoflow.

### Target Audience

- Developers with basic Python knowledge
- Those who have experience with Polars or are willing to learn
- Anyone looking to automate data processing workflows

### What You'll Learn

- Basic structure and types of plugins
- How to implement InputPlugin, TransformPlugin, and OutputPlugin
- Multi-stream processing with the label feature
- Best practices for error handling and testing
- Plugin packaging and distribution methods

---

## 2. Plugin Basics

### 2.1 Plugin Types

Cryoflow has three types of plugins.

#### InputPlugin (Input Plugin)

- **Role**: Loads data from a data source and produces FrameData
- **Use cases**: File reading (Parquet/IPC/CSV, etc.), database queries, etc.
- **Characteristics**: `execute` takes no arguments. Returning a LazyFrame is recommended

#### TransformPlugin (Transformation Plugin)

- **Role**: Receives a data frame and returns a transformed data frame
- **Use cases**: Filtering, column addition, aggregation, joins, etc.
- **Characteristics**: Builds a computation graph (LazyFrame) - actual computation is executed in OutputPlugin

#### OutputPlugin (Output Plugin)

- **Role**: Receives a data frame and outputs it to files, databases, etc.
- **Use cases**: Parquet/CSV/IPC output, database writes, API submissions, etc.
- **Characteristics**: Calls `collect()` or `sink_*()` to actually execute data processing

**Plugin type comparison:**

| Plugin Type | execute Arguments | execute Return Value | Role |
|---|---|---|---|
| **InputPlugin** | none | `Result[FrameData, Exception]` | Generates / loads data |
| **TransformPlugin** | `df: FrameData` | `Result[FrameData, Exception]` | Transforms data |
| **OutputPlugin** | `df: FrameData` | `Result[None, Exception]` | Outputs data |

### 2.2 Basic Architecture

All plugins implement the following common interface.

```python
from abc import ABC, abstractmethod
from typing import Any

from cryoflow_plugin_collections.libs.polars import pl, DataType
from cryoflow_plugin_collections.libs.returns import Result
from cryoflow_plugin_collections.libs.core import FrameData

# FrameData is defined in cryoflow_plugin_collections.libs.core
# FrameData = pl.LazyFrame | pl.DataFrame

class BasePlugin(ABC):
    def __init__(self, options: dict[str, Any], config_dir: Path) -> None:
        """Initialize the plugin

        Args:
            options: Plugin-specific options from configuration file
            config_dir: Directory containing the configuration file (for path resolution)
        """
        self.options = options
        self._config_dir = config_dir

    def resolve_path(self, path: str | Path) -> Path:
        """Resolve a path relative to the configuration file directory

        Absolute paths are returned as-is, relative paths are resolved
        relative to the configuration file's directory.

        Args:
            path: Path to resolve

        Returns:
            Resolved absolute path
        """
        path = Path(path)
        if not path.is_absolute():
            path = self._config_dir / path
        return path.resolve()

    @abstractmethod
    def name(self) -> str:
        """Return the plugin identifier name"""

    @abstractmethod
    def dry_run(self, schema: dict[str, DataType]) -> Result[dict[str, DataType], Exception]:
        """Validate schema and return expected output schema"""
```

### 2.3 Plugin Lifecycle

```
1. Load configuration file
   ↓
2. Load plugins (importlib)
   ↓
3. Instantiate plugins (__init__ is called)
   ↓
4. [Optional] Pre-validation via dry_run (cryoflow check)
   ↓
5. Execute InputPlugin (data loading)
   ↓
6. Execute TransformPlugin (data transformation)
   ↓
7. Execute OutputPlugin (data output)
```

---

## 3. Development Environment Setup

### 3.1 Required Packages

Plugin development requires only the `cryoflow-plugin-collections` package. This package re-exports all necessary libraries for plugin development (`polars`, `returns`, `cryoflow-core`).

```toml
[project]
dependencies = [
    "cryoflow-plugin-collections",  # Plugin development library (includes polars, returns, cryoflow-core)
]

[project.optional-dependencies]
dev = [
    # Test-related packages are optional (choose based on developer preference)
    "pytest>=8.0.0",         # Test framework (recommended)
    "pytest-cov>=5.0.0",     # Coverage measurement (optional)
]
```

**Import Methods**:

```python
# Import Polars
from cryoflow_plugin_collections.libs.polars import pl

# Import Result types
from cryoflow_plugin_collections.libs.returns import Result, Success, Failure

# Import base classes and type definitions
from cryoflow_plugin_collections.libs.core import (
    InputPlugin,
    TransformPlugin,
    OutputPlugin,
    FrameData,
)
```

**Note**: You don't need to add `polars` or `returns` as direct dependencies. Use the ones provided by `cryoflow-plugin-collections`.

### 3.2 Project Structure

Recommended project structure:

```
my-cryoflow-plugins/
├── pyproject.toml
├── my_plugins/
│   ├── __init__.py
│   ├── input/
│   │   ├── __init__.py
│   │   └── my_input.py        # InputPlugin implementation
│   ├── transform/
│   │   ├── __init__.py
│   │   └── my_transform.py    # TransformPlugin implementation
│   └── output/
│       ├── __init__.py
│       └── my_output.py        # OutputPlugin implementation
└── tests/
    ├── test_input.py
    ├── test_transform.py
    └── test_output.py
```

---

## 4. InputPlugin Implementation Guide

### 4.1 Label Feature and Multi-Stream Processing

All plugins have a `label` (default: `'default'`).

The `label` is used to **identify multiple input data streams**. Plugins with the same label are linked together:

```
InputPlugin(label='sales')  →  data_map['sales']  →  TransformPlugin(label='sales')
InputPlugin(label='master') →  data_map['master'] →  TransformPlugin(label='master')
```

For a single data stream, omit `label` or use `'default'`.

### 4.2 Basic Implementation

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

### 4.3 Example: CSV File Reader Plugin

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

## 5. TransformPlugin Implementation Guide

### 5.1 Basic Implementation

TransformPlugin requires implementation of the following three methods.

```python
from cryoflow_plugin_collections.libs.polars import pl
from cryoflow_plugin_collections.libs.returns import Result, Success, Failure
from cryoflow_plugin_collections.libs.core import TransformPlugin, FrameData

class MyTransformPlugin(TransformPlugin):
    def name(self) -> str:
        """Plugin identifier name (used in logs and error messages)"""
        return 'my_transform'

    def execute(self, df: FrameData) -> Result[FrameData, Exception]:
        """Core data transformation logic"""
        try:
            # Get configuration from self.options
            column = self.options.get('column_name')
            if column is None:
                return Failure(ValueError("Option 'column_name' is required"))

            # Data transformation
            transformed = df.with_columns(
                pl.col(column).str.to_uppercase().alias(column)
            )
            return Success(transformed)
        except Exception as e:
            return Failure(e)

    def dry_run(self, schema: dict[str, DataType]) -> Result[dict[str, DataType], Exception]:
        """Schema validation (pre-check without touching actual data)"""
        try:
            column = self.options.get('column_name')
            if column is None:
                return Failure(ValueError("Option 'column_name' is required"))

            # Check column existence
            if column not in schema:
                return Failure(ValueError(f"Column '{column}' not found in schema"))

            # Type check
            if schema[column] != pl.Utf8:
                return Failure(ValueError(
                    f"Column '{column}' must be String type, got {schema[column]}"
                ))

            # This plugin doesn't modify schema, so return as-is
            return Success(schema)
        except Exception as e:
            return Failure(e)
```

### 5.2 Example: Column Multiplier Plugin

Let's look at a real implementation example that multiplies a numeric column by a coefficient.

```python
"""Transformation plugin that multiplies a specified column by a coefficient"""

from cryoflow_plugin_collections.libs.polars import pl
from cryoflow_plugin_collections.libs.returns import Failure, Result, Success
from cryoflow_plugin_collections.libs.core import FrameData, TransformPlugin


class ColumnMultiplierPlugin(TransformPlugin):
    """Multiply a specified numeric column by a coefficient

    Options:
        column_name (str): Target column name
        multiplier (float | int): Multiplication coefficient
    """

    def name(self) -> str:
        return 'column_multiplier'

    def execute(self, df: FrameData) -> Result[FrameData, Exception]:
        """Transform the data frame

        Args:
            df: Input LazyFrame or DataFrame

        Returns:
            Result containing transformed data, or Exception on failure
        """
        try:
            column_name = self.options.get('column_name')
            multiplier = self.options.get('multiplier')

            # Validate options
            if column_name is None:
                return Failure(ValueError("Option 'column_name' is required"))
            if multiplier is None:
                return Failure(ValueError("Option 'multiplier' is required"))

            # Transform data (add to LazyFrame computation graph)
            transformed = df.with_columns(
                (pl.col(column_name) * multiplier).alias(column_name)
            )
            return Success(transformed)
        except Exception as e:
            return Failure(e)

    def dry_run(self, schema: dict[str, DataType]) -> Result[dict[str, DataType], Exception]:
        """Validate schema and return expected output schema

        Args:
            schema: Input schema (column_name -> DataType mapping)

        Returns:
            Result containing output schema, or Exception on failure
        """
        try:
            column_name = self.options.get('column_name')
            multiplier = self.options.get('multiplier')

            # Validate options
            if column_name is None:
                return Failure(ValueError("Option 'column_name' is required"))
            if multiplier is None:
                return Failure(ValueError("Option 'multiplier' is required"))

            # Check column existence
            if column_name not in schema:
                return Failure(
                    ValueError(f"Column '{column_name}' not found in schema")
                )

            # Type check (only numeric types allowed)
            dtype = schema[column_name]
            numeric_types = (
                pl.Int8, pl.Int16, pl.Int32, pl.Int64,
                pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64,
                pl.Float32, pl.Float64,
            )
            if not (isinstance(dtype, numeric_types) or type(dtype) in numeric_types):
                return Failure(
                    ValueError(
                        f"Column '{column_name}' has type {dtype}, "
                        "expected numeric type"
                    )
                )

            # This plugin doesn't modify schema
            return Success(schema)
        except Exception as e:
            return Failure(e)
```

### 5.3 Leveraging LazyFrame

In TransformPlugin, avoid touching actual data and only build computation graphs.

```python
def execute(self, df: FrameData) -> Result[FrameData, Exception]:
    try:
        # ❌ Avoid: calling collect() executes immediately
        # materialized = df.collect()
        # filtered = materialized.filter(pl.col("value") > 100)
        # return Success(filtered.lazy())

        # ✅ Recommended: build computation graph with LazyFrame method chains
        filtered = df.filter(pl.col("value") > 100)
        return Success(filtered)
    except Exception as e:
        return Failure(e)
```

**Key Points**:
- Don't call `collect()` (it's called in OutputPlugin)
- Build computation graphs with method chains
- Allows Polars optimization engine to optimize the entire pipeline

---

## 6. OutputPlugin Implementation Guide

### 6.1 Basic Implementation

OutputPlugin is similar to TransformPlugin but has a different return type.

```python
from pathlib import Path

from cryoflow_plugin_collections.libs.polars import pl
from cryoflow_plugin_collections.libs.returns import Result, Success, Failure
from cryoflow_plugin_collections.libs.core import OutputPlugin, FrameData

class MyOutputPlugin(OutputPlugin):
    def name(self) -> str:
        return 'my_output'

    def execute(self, df: FrameData) -> Result[None, Exception]:
        """Output data (collect/sink is called here for the first time)"""
        try:
            # resolve_path()を使用して、相対パスを設定ファイル基準で解決
            output_path = self.resolve_path(self.options.get('output_path'))

            # Create directory
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Use sink_* for LazyFrame, write_* for DataFrame
            if isinstance(df, pl.LazyFrame):
                df.sink_parquet(output_path)
            else:
                df.write_parquet(output_path)

            return Success(None)
        except Exception as e:
            return Failure(e)

    def dry_run(self, schema: dict[str, DataType]) -> Result[dict[str, DataType], Exception]:
        """Validate writability of output destination"""
        try:
            # resolve_path()を使用して、相対パスを設定ファイル基準で解決
            output_path = self.resolve_path(self.options.get('output_path'))

            # Check if parent directory can be created
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return Failure(
                    ValueError(f"Cannot create directory {output_path.parent}: {e}")
                )

            # OutputPlugin doesn't modify schema
            return Success(schema)
        except Exception as e:
            return Failure(e)
```

### 6.2 Example: Parquet Writer Plugin

```python
"""Parquet file output plugin"""

from pathlib import Path

from cryoflow_plugin_collections.libs.polars import pl
from cryoflow_plugin_collections.libs.returns import Failure, Result, Success
from cryoflow_plugin_collections.libs.core import FrameData, OutputPlugin


class ParquetWriterPlugin(OutputPlugin):
    """Write data frame to Parquet file

    Options:
        output_path (str | Path): Path to output Parquet file
    """

    def name(self) -> str:
        return 'parquet_writer'

    def execute(self, df: FrameData) -> Result[None, Exception]:
        """Write data frame to Parquet file

        Args:
            df: Input LazyFrame or DataFrame

        Returns:
            Result containing None on success, or Exception on failure
        """
        try:
            output_path_opt = self.options.get('output_path')
            if output_path_opt is None:
                return Failure(ValueError("Option 'output_path' is required"))

            # resolve_path() to resolve relative paths relative to config file
            output_path = self.resolve_path(output_path_opt)

            # Create parent directory
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write based on frame type
            if isinstance(df, pl.LazyFrame):
                # Streaming write (memory efficient)
                df.sink_parquet(output_path)
            else:  # DataFrame
                df.write_parquet(output_path)

            return Success(None)
        except Exception as e:
            return Failure(e)

    def dry_run(self, schema: dict[str, DataType]) -> Result[dict[str, DataType], Exception]:
        """Validate output destination writability

        Args:
            schema: Input schema (OutputPlugin doesn't modify it)

        Returns:
            Result containing input schema unchanged, or Exception on failure
        """
        try:
            output_path_opt = self.options.get('output_path')
            if output_path_opt is None:
                return Failure(ValueError("Option 'output_path' is required"))

            # resolve_path() to resolve relative paths relative to config file
            output_path = self.resolve_path(output_path_opt)

            # Check if parent directory can be created
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return Failure(
                    ValueError(
                        f"Cannot create parent directory for {output_path}: {e}"
                    )
                )

            return Success(schema)
        except Exception as e:
            return Failure(e)
```

---

## 7. dry_run Method Implementation

### 7.1 Purpose and Role

The `dry_run` method validates the following without processing actual data:

- Configuration option validity
- Required column existence
- Column types
- Output destination writability

This allows detecting problems before actual execution (`cryoflow check` command).

### 7.2 Implementation Patterns

#### Pattern 1: Plugin that doesn't modify schema

```python
from cryoflow_plugin_collections.libs.polars import DataType
from cryoflow_plugin_collections.libs.returns import Result, Success, Failure

def dry_run(self, schema: dict[str, DataType]) -> Result[dict[str, DataType], Exception]:
    """Processing that doesn't change schema, such as filtering"""
    try:
        # Validate options
        threshold = self.options.get('threshold')
        if threshold is None:
            return Failure(ValueError("Option 'threshold' is required"))

        # Check column existence
        column = self.options.get('column_name')
        if column not in schema:
            return Failure(ValueError(f"Column '{column}' not found"))

        # Type check
        if not schema[column].is_numeric():
            return Failure(ValueError(f"Column '{column}' must be numeric"))

        # Schema is unchanged
        return Success(schema)
    except Exception as e:
        return Failure(e)
```

#### Pattern 2: Plugin that adds columns

```python
from cryoflow_plugin_collections.libs.polars import pl, DataType
from cryoflow_plugin_collections.libs.returns import Result, Success, Failure

def dry_run(self, schema: dict[str, DataType]) -> Result[dict[str, DataType], Exception]:
    """Processing that adds new columns"""
    try:
        new_column = self.options.get('new_column_name', 'computed_value')

        # Check for duplicates
        if new_column in schema:
            return Failure(ValueError(f"Column '{new_column}' already exists"))

        # Create new schema
        new_schema = schema.copy()
        new_schema[new_column] = pl.Float64

        return Success(new_schema)
    except Exception as e:
        return Failure(e)
```

#### Pattern 3: Plugin that removes columns

```python
from cryoflow_plugin_collections.libs.polars import DataType
from cryoflow_plugin_collections.libs.returns import Result, Success, Failure

def dry_run(self, schema: dict[str, DataType]) -> Result[dict[str, DataType], Exception]:
    """Processing that removes columns"""
    try:
        drop_columns = self.options.get('drop_columns', [])

        # Check existence
        for col in drop_columns:
            if col not in schema:
                return Failure(ValueError(f"Column '{col}' not found"))

        # Create new schema
        new_schema = {k: v for k, v in schema.items() if k not in drop_columns}

        return Success(new_schema)
    except Exception as e:
        return Failure(e)
```

---

## 8. Error Handling

### 8.1 Using Result Type

Cryoflow uses the `Result` type from the `returns` library to unify error handling.

```python
from cryoflow_plugin_collections.libs.returns import Result, Success, Failure

# On success
return Success(transformed_df)

# On failure
return Failure(ValueError("Invalid configuration"))
```

**Benefits**:
- Control exception propagation
- Type-safe error handling
- Consistent error handling across the pipeline

### 8.2 Error Message Best Practices

#### ✅ Good Error Messages

```python
# Include specific information
return Failure(ValueError(
    f"Column '{column_name}' not found in schema. "
    f"Available columns: {', '.join(schema.keys())}"
))

# Show expected and actual values
return Failure(ValueError(
    f"Column '{column_name}' has type {actual_type}, "
    f"expected {expected_type}"
))

# Suggest solutions
return Failure(ValueError(
    f"Option 'output_path' is required. "
    f"Add 'output_path = \"path/to/file.parquet\"' to plugin options."
))
```

#### ❌ Error Messages to Avoid

```python
# Insufficient information
return Failure(ValueError("Column not found"))

# Unclear what the problem is
return Failure(ValueError("Invalid input"))

# Too technical (users can't understand)
return Failure(ValueError("Schema validation failed at line 42"))
```

### 8.3 Common Error Patterns

```python
def execute(self, df: FrameData) -> Result[FrameData, Exception]:
    try:
        # 1. Validate options
        required_opt = self.options.get('required_option')
        if required_opt is None:
            return Failure(ValueError("Option 'required_option' is required"))

        # 2. Check column existence (Polars throws exception)
        try:
            result = df.select(pl.col(required_opt))
        except pl.exceptions.ColumnNotFoundError as e:
            return Failure(ValueError(
                f"Column '{required_opt}' not found. Available: {df.columns}"
            ))

        # 3. Type check
        dtype = df.schema[required_opt]
        if not dtype.is_numeric():
            return Failure(ValueError(
                f"Column '{required_opt}' must be numeric, got {dtype}"
            ))

        # 4. Range check
        threshold = self.options.get('threshold', 0)
        if threshold < 0:
            return Failure(ValueError(
                f"Option 'threshold' must be non-negative, got {threshold}"
            ))

        # Execute processing
        transformed = df.filter(pl.col(required_opt) > threshold)
        return Success(transformed)

    except Exception as e:
        # Catch unexpected exceptions
        return Failure(e)
```

---

## 9. Writing Tests

### 9.1 Basic Test Structure

Use pytest to test plugins.

```python
import pytest

from cryoflow_plugin_collections.libs.polars import pl
from cryoflow_plugin_collections.libs.returns import Success, Failure

from my_plugins.transform.my_transform import MyTransformPlugin


class TestMyTransformPlugin:
    """Test suite for MyTransformPlugin"""

    @pytest.fixture
    def plugin(self):
        """Create plugin instance"""
        return MyTransformPlugin(options={
            'column_name': 'test_column',
            'multiplier': 2
        })

    @pytest.fixture
    def sample_df(self):
        """Create test data frame"""
        return pl.DataFrame({
            'test_column': [1, 2, 3],
            'other_column': ['a', 'b', 'c']
        })

    def test_name(self, plugin):
        """Plugin name should be correct"""
        assert plugin.name() == 'my_transform'

    def test_execute_success(self, plugin, sample_df):
        """Normal transformation should succeed"""
        result = plugin.execute(sample_df.lazy())

        assert isinstance(result, Success)
        df = result.unwrap().collect()
        assert df['test_column'].to_list() == [2, 4, 6]

    def test_execute_missing_option(self):
        """Should return error when required option is missing"""
        plugin = MyTransformPlugin(options={})
        df = pl.DataFrame({'col': [1, 2, 3]}).lazy()

        result = plugin.execute(df)

        assert isinstance(result, Failure)
        assert "required" in str(result.failure()).lower()

    def test_dry_run_success(self, plugin):
        """Schema validation should succeed"""
        schema = {'test_column': pl.Int64, 'other_column': pl.Utf8}

        result = plugin.dry_run(schema)

        assert isinstance(result, Success)
        assert result.unwrap() == schema

    def test_dry_run_column_not_found(self, plugin):
        """Should return error when specifying non-existent column"""
        schema = {'other_column': pl.Utf8}

        result = plugin.dry_run(schema)

        assert isinstance(result, Failure)
        assert "not found" in str(result.failure()).lower()

    def test_dry_run_invalid_type(self):
        """Should return error when specifying column with invalid type"""
        plugin = MyTransformPlugin(options={
            'column_name': 'string_column',
            'multiplier': 2
        })
        schema = {'string_column': pl.Utf8}

        result = plugin.dry_run(schema)

        assert isinstance(result, Failure)
        assert "numeric" in str(result.failure()).lower()
```

### 9.2 Implementation Example

```python
"""Tests for ColumnMultiplierPlugin"""

import pytest

from cryoflow_plugin_collections.libs.polars import pl
from cryoflow_plugin_collections.libs.returns import Failure, Success
from cryoflow_plugin_collections.transform.multiplier import ColumnMultiplierPlugin


class TestColumnMultiplierPlugin:
    @pytest.fixture
    def plugin(self):
        return ColumnMultiplierPlugin(options={
            'column_name': 'value',
            'multiplier': 3
        })

    @pytest.fixture
    def sample_lazy_df(self):
        return pl.DataFrame({
            'value': [1, 2, 3, 4, 5],
            'name': ['a', 'b', 'c', 'd', 'e']
        }).lazy()

    def test_name(self, plugin):
        assert plugin.name() == 'column_multiplier'

    def test_execute_with_lazyframe(self, plugin, sample_lazy_df):
        result = plugin.execute(sample_lazy_df)

        assert isinstance(result, Success)
        df = result.unwrap().collect()
        assert df['value'].to_list() == [3, 6, 9, 12, 15]
        assert df['name'].to_list() == ['a', 'b', 'c', 'd', 'e']

    def test_execute_missing_column_name(self, sample_lazy_df):
        plugin = ColumnMultiplierPlugin(options={'multiplier': 2})
        result = plugin.execute(sample_lazy_df)

        assert isinstance(result, Failure)
        error = result.failure()
        assert "'column_name' is required" in str(error)

    def test_execute_missing_multiplier(self, sample_lazy_df):
        plugin = ColumnMultiplierPlugin(options={'column_name': 'value'})
        result = plugin.execute(sample_lazy_df)

        assert isinstance(result, Failure)
        error = result.failure()
        assert "'multiplier' is required" in str(error)

    def test_dry_run_success(self, plugin):
        schema = {'value': pl.Int64, 'name': pl.Utf8}
        result = plugin.dry_run(schema)

        assert isinstance(result, Success)
        assert result.unwrap() == schema

    def test_dry_run_column_not_found(self, plugin):
        schema = {'other': pl.Int64}
        result = plugin.dry_run(schema)

        assert isinstance(result, Failure)
        assert "not found in schema" in str(result.failure())

    def test_dry_run_invalid_type(self):
        plugin = ColumnMultiplierPlugin(options={
            'column_name': 'name',
            'multiplier': 2
        })
        schema = {'name': pl.Utf8, 'value': pl.Int64}
        result = plugin.dry_run(schema)

        assert isinstance(result, Failure)
        assert "expected numeric type" in str(result.failure())
```

---

## 10. Plugin Distribution

### 10.1 Package Structure

```
my-cryoflow-plugins/
├── README.md
├── LICENSE
├── pyproject.toml
├── my_cryoflow_plugins/
│   ├── __init__.py
│   ├── input/
│   │   ├── __init__.py
│   │   └── my_input.py
│   ├── transform/
│   │   ├── __init__.py
│   │   └── my_transform.py
│   └── output/
│       ├── __init__.py
│       └── my_output.py
└── tests/
    ├── test_input.py
    ├── test_transform.py
    └── test_output.py
```

### 10.2 Dependency Definition

Example `pyproject.toml` configuration:

```toml
[project]
name = "my-cryoflow-plugins"
version = "0.1.0"
description = "Custom plugins for Cryoflow"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "cryoflow-plugin-collections>=0.1.0",  # Plugin development library
]

[project.optional-dependencies]
dev = [
    # Test libraries are optional
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### 10.3 Distribution Methods

#### Method 1: Publish to PyPI

```bash
# Build
python -m build

# Upload to PyPI (account required)
python -m twine upload dist/*
```

Users can install with `pip install`:

```bash
pip install my-cryoflow-plugins
```

#### Method 2: Install directly from Git repository

```bash
pip install git+https://github.com/username/my-cryoflow-plugins.git
```

#### Method 3: Development install from local directory

```bash
cd my-cryoflow-plugins
pip install -e .
```

---

## 11. Using in Configuration Files

Once you've implemented a plugin, you can use it in `config.toml`.

### Basic Usage Example

```toml
# InputPlugin configuration
[[input_plugins]]
name = "parquet-input"
module = "cryoflow_plugin_collections.input.parquet_scan"
enabled = true
[input_plugins.options]
input_path = "data/input.parquet"

# TransformPlugin configuration
[[transform_plugins]]
name = "my-transform"
module = "my_cryoflow_plugins.transform.my_transform"
enabled = true
[transform_plugins.options]
column_name = "value"
multiplier = 2

# OutputPlugin configuration
[[output_plugins]]
name = "my-output"
module = "my_cryoflow_plugins.output.my_output"
enabled = true
[output_plugins.options]
output_path = "data/output.parquet"
```

### Chaining Multiple Plugins

TransformPlugins are chained in definition order. Each OutputPlugin receives the same transformed data (fan-out).

```toml
# InputPlugin configuration
[[input_plugins]]
name = "sales-input"
module = "cryoflow_plugin_collections.input.parquet_scan"
enabled = true
[input_plugins.options]
input_path = "data/sales.parquet"

# Filtering
[[transform_plugins]]
name = "filter-high-value"
module = "my_plugins.transform.filter"
enabled = true
[transform_plugins.options]
column_name = "total_amount"
threshold = 1000

# Add column
[[transform_plugins]]
name = "add-tax"
module = "my_plugins.transform.tax_calculator"
enabled = true
[transform_plugins.options]
amount_column = "total_amount"
tax_rate = 0.1
output_column = "tax"

# Aggregation
[[transform_plugins]]
name = "aggregate"
module = "my_plugins.transform.aggregator"
enabled = true
[transform_plugins.options]
group_by = ["region", "category"]
agg_columns = ["total_amount", "tax"]

# Output (multiple definitions supported: same data is passed to each OutputPlugin)
[[output_plugins]]
name = "parquet-writer"
module = "my_plugins.output.parquet_writer"
enabled = true
[output_plugins.options]
output_path = "data/processed.parquet"

[[output_plugins]]
name = "ipc-writer"
module = "my_plugins.output.ipc_writer"
enabled = true
[output_plugins.options]
output_path = "data/processed.ipc"
```

### Multi-Stream Configuration Example

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

### Using Filesystem Paths

You can also specify file paths directly without installing the module as a Python package.

```toml
[[transform_plugins]]
name = "local-plugin"
module = "./my_local_plugins/transform.py"
enabled = true
[transform_plugins.options]
some_option = "value"

[[output_plugins]]
name = "absolute-path-plugin"
module = "/home/user/plugins/my_output_plugin.py"
enabled = true
```

---

## 12. Reference

### 12.1 Type Definitions

```python
# Types re-exported from cryoflow_plugin_collections.libs
from typing import Any

from cryoflow_plugin_collections.libs.polars import pl, DataType
from cryoflow_plugin_collections.libs.returns import Result
from cryoflow_plugin_collections.libs.core import FrameData

# DataFrame type (LazyFrame or DataFrame)
# Defined as FrameData = pl.LazyFrame | pl.DataFrame

# Schema type (column name -> data type mapping)
Schema = dict[str, DataType]

# Plugin options type
PluginOptions = dict[str, Any]
```

### 12.2 Base Class API

#### BasePlugin

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from cryoflow_plugin_collections.libs.polars import DataType
from cryoflow_plugin_collections.libs.returns import Result

class BasePlugin(ABC):
    def __init__(self, options: dict[str, Any], config_dir: Path) -> None:
        """Initialize the plugin

        Args:
            options: Plugin-specific options passed from configuration file
            config_dir: Directory containing the configuration file (for path resolution)
        """
        self.options = options
        self._config_dir = config_dir

    def resolve_path(self, path: str | Path) -> Path:
        """Resolve a path relative to the configuration file directory

        Absolute paths are returned as-is, relative paths are resolved
        relative to the configuration file's directory.

        Args:
            path: Path to resolve (string or Path object)

        Returns:
            Resolved absolute path

        Example:
            >>> # If config.toml is at /project/config/config.toml
            >>> output_path = self.resolve_path("data/output.parquet")
            >>> # => /project/config/data/output.parquet
        """
        path = Path(path)
        if not path.is_absolute():
            path = self._config_dir / path
        return path.resolve()

    @abstractmethod
    def name(self) -> str:
        """Return plugin identifier name

        Returns:
            Plugin name (used in logs and error messages)
        """

    @abstractmethod
    def dry_run(self, schema: dict[str, DataType]) -> Result[dict[str, DataType], Exception]:
        """Perform schema validation

        Args:
            schema: Input schema

        Returns:
            Success: Expected output schema
            Failure: Validation error
        """
```

#### InputPlugin

```python
from cryoflow_plugin_collections.libs.core import InputPlugin, FrameData
from cryoflow_plugin_collections.libs.returns import Result
import polars as pl

class InputPlugin(BasePlugin):
    @abstractmethod
    def execute(self) -> Result[FrameData, Exception]:
        """Load and return data as FrameData.

        Takes no arguments. Generates data directly from the data source.

        Returns:
            Success: Loaded data frame (LazyFrame preferred)
            Failure: Loading error

        Note:
            - Process as LazyFrame whenever possible
            - Don't call collect() (it's called in OutputPlugin)
        """

    @abstractmethod
    def dry_run(self) -> Result[dict[str, pl.DataType], Exception]:
        """Return schema without loading actual data.

        Takes no arguments. Reads only file metadata.

        Returns:
            Success: Schema (column name → DataType mapping)
            Failure: Schema retrieval error
        """
```

#### TransformPlugin

```python
from cryoflow_plugin_collections.libs.core import TransformPlugin, FrameData
from cryoflow_plugin_collections.libs.returns import Result

class TransformPlugin(BasePlugin):
    @abstractmethod
    def execute(self, df: FrameData) -> Result[FrameData, Exception]:
        """Transform the data frame

        Args:
            df: Input data frame (LazyFrame or DataFrame)

        Returns:
            Success: Transformed data frame
            Failure: Processing error

        Note:
            - Process as LazyFrame whenever possible
            - Don't call collect() (it's called in OutputPlugin)
        """
```

#### OutputPlugin

```python
from cryoflow_plugin_collections.libs.core import OutputPlugin, FrameData
from cryoflow_plugin_collections.libs.returns import Result

class OutputPlugin(BasePlugin):
    @abstractmethod
    def execute(self, df: FrameData) -> Result[None, Exception]:
        """Output the data frame

        Args:
            df: Input data frame (LazyFrame or DataFrame)

        Returns:
            Success: None (output succeeded)
            Failure: Output error

        Note:
            - Call collect() or sink_*() here
            - Manage resources (file handlers, etc.) with with statements
        """
```

### Built-in Plugins

Built-in plugins included in the `cryoflow-plugin-collections` package:

| Plugin | Module |
|---|---|
| IPC (Arrow) input | `cryoflow_plugin_collections.input.ipc_scan` |
| Parquet input | `cryoflow_plugin_collections.input.parquet_scan` |

### 12.3 Polars Method Reference

Commonly used Polars methods in plugin development:

#### LazyFrame Methods

```python
from cryoflow_plugin_collections.libs.polars import pl

# Column selection
df.select(pl.col("column_name"))
df.select(pl.col("col1"), pl.col("col2"))

# Filtering
df.filter(pl.col("value") > 100)
df.filter((pl.col("a") > 10) & (pl.col("b") < 20))

# Add/modify columns
df.with_columns(pl.col("value") * 2)
df.with_columns((pl.col("a") + pl.col("b")).alias("sum"))

# Drop columns
df.drop("column_name")

# Aggregation
df.group_by("category").agg(pl.col("value").sum())

# Join
df.join(other_df, on="key")

# Sort
df.sort("column_name", descending=True)

# Execute (only use in OutputPlugin)
df.collect()  # Convert to DataFrame
df.sink_parquet("output.parquet")  # Streaming write
```

#### DataFrame Methods

```python
# Convert to LazyFrame
df.lazy()

# File output
df.write_parquet("output.parquet")
df.write_csv("output.csv")
df.write_ipc("output.arrow")
```

#### Expression Construction

```python
# Column reference
pl.col("column_name")

# Arithmetic operations
pl.col("a") + pl.col("b")
pl.col("value") * 2

# String operations
pl.col("name").str.to_uppercase()
pl.col("text").str.contains("pattern")

# Conditional branching
pl.when(pl.col("value") > 100).then(pl.lit("high")).otherwise(pl.lit("low"))

# Aggregation functions
pl.col("value").sum()
pl.col("value").mean()
pl.col("value").max()
pl.col("value").count()

# Alias (rename column)
pl.col("old_name").alias("new_name")
```

---

## Summary

This guide explained how to develop Cryoflow plugins.

### What You Learned

- ✅ Basic structure and types of plugins (InputPlugin / TransformPlugin / OutputPlugin)
- ✅ How to implement InputPlugin and the label feature for multi-stream processing
- ✅ How to implement TransformPlugin and OutputPlugin
- ✅ Pre-validation with dry_run method
- ✅ Error handling with Result type
- ✅ How to write tests
- ✅ Packaging and distribution methods

### Next Steps

1. **Create a simple plugin**
   - Start by referencing samples in `examples/`
   - Begin with basic operations like filtering or column addition

2. **Read existing plugins**
   - Reference code in `cryoflow-plugin-collections`
   - Also check test code

3. **Challenge yourself with complex plugins**
   - External API integration
   - Complex aggregation processing
   - Custom output formats

4. **Contribute to the community**
   - Publish useful plugins
   - Report bugs or suggest improvements

### References

- [Cryoflow Repository](https://github.com/yasunori0418/cryoflow)
- [Polars Documentation](https://docs.pola.rs/)
- [returns Library](https://returns.readthedocs.io/)
- [pluggy Documentation](https://pluggy.readthedocs.io/)

---

Questions and feedback are welcome on GitHub Issues!
