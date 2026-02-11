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
- [4. TransformPlugin Implementation Guide](#4-transformplugin-implementation-guide)
  - [4.1 Basic Implementation](#41-basic-implementation)
  - [4.2 Example: Column Multiplier Plugin](#42-example-column-multiplier-plugin)
  - [4.3 Leveraging LazyFrame](#43-leveraging-lazyframe)
- [5. OutputPlugin Implementation Guide](#5-outputplugin-implementation-guide)
  - [5.1 Basic Implementation](#51-basic-implementation)
  - [5.2 Example: Parquet Writer Plugin](#52-example-parquet-writer-plugin)
- [6. dry_run Method Implementation](#6-dry_run-method-implementation)
  - [6.1 Purpose and Role](#61-purpose-and-role)
  - [6.2 Implementation Patterns](#62-implementation-patterns)
- [7. Error Handling](#7-error-handling)
  - [7.1 Using Result Type](#71-using-result-type)
  - [7.2 Error Message Best Practices](#72-error-message-best-practices)
  - [7.3 Common Error Patterns](#73-common-error-patterns)
- [8. Writing Tests](#8-writing-tests)
  - [8.1 Basic Test Structure](#81-basic-test-structure)
  - [8.2 Implementation Example](#82-implementation-example)
- [9. Plugin Distribution](#9-plugin-distribution)
  - [9.1 Package Structure](#91-package-structure)
  - [9.2 Dependency Definition](#92-dependency-definition)
  - [9.3 Distribution Methods](#93-distribution-methods)
- [10. Using in Configuration Files](#10-using-in-configuration-files)
- [11. Reference](#11-reference)
  - [11.1 Type Definitions](#111-type-definitions)
  - [11.2 Base Class API](#112-base-class-api)
  - [11.3 Polars Method Reference](#113-polars-method-reference)

---

## 1. Introduction

Cryoflow is a plugin-driven, column-oriented data processing CLI tool built on Polars LazyFrame. This guide explains how to develop custom plugins for Cryoflow.

### Target Audience

- Developers with basic Python knowledge
- Those who have experience with Polars or are willing to learn
- Anyone looking to automate data processing workflows

### What You'll Learn

- Basic structure and types of plugins
- How to implement TransformPlugin and OutputPlugin
- Best practices for error handling and testing
- Plugin packaging and distribution methods

---

## 2. Plugin Basics

### 2.1 Plugin Types

Cryoflow has two types of plugins.

#### TransformPlugin (Transformation Plugin)

- **Role**: Receives a data frame and returns a transformed data frame
- **Use cases**: Filtering, column addition, aggregation, joins, etc.
- **Characteristics**: Builds a computation graph (LazyFrame) - actual computation is executed in OutputPlugin

#### OutputPlugin (Output Plugin)

- **Role**: Receives a data frame and outputs it to files, databases, etc.
- **Use cases**: Parquet/CSV/IPC output, database writes, API submissions, etc.
- **Characteristics**: Calls `collect()` or `sink_*()` to actually execute data processing

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
    def __init__(self, options: dict[str, Any]) -> None:
        self.options = options

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
5. Execute execute method (cryoflow run)
   ↓
6. Output results
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
│   ├── transform/
│   │   ├── __init__.py
│   │   └── my_transform.py    # TransformPlugin implementation
│   └── output/
│       ├── __init__.py
│       └── my_output.py        # OutputPlugin implementation
└── tests/
    ├── test_transform.py
    └── test_output.py
```

---

## 4. TransformPlugin Implementation Guide

### 4.1 Basic Implementation

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

### 4.2 Example: Column Multiplier Plugin

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

### 4.3 Leveraging LazyFrame

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

## 5. OutputPlugin Implementation Guide

### 5.1 Basic Implementation

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
            output_path = Path(self.options.get('output_path'))

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
            output_path = Path(self.options.get('output_path'))

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

### 5.2 Example: Parquet Writer Plugin

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

            output_path = Path(output_path_opt)

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

            output_path = Path(output_path_opt)

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

## 6. dry_run Method Implementation

### 6.1 Purpose and Role

The `dry_run` method validates the following without processing actual data:

- Configuration option validity
- Required column existence
- Column types
- Output destination writability

This allows detecting problems before actual execution (`cryoflow check` command).

### 6.2 Implementation Patterns

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

## 7. Error Handling

### 7.1 Using Result Type

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

### 7.2 Error Message Best Practices

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

### 7.3 Common Error Patterns

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

## 8. Writing Tests

### 8.1 Basic Test Structure

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

### 8.2 Implementation Example

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

## 9. Plugin Distribution

### 9.1 Package Structure

```
my-cryoflow-plugins/
├── README.md
├── LICENSE
├── pyproject.toml
├── my_cryoflow_plugins/
│   ├── __init__.py
│   ├── transform/
│   │   ├── __init__.py
│   │   └── my_transform.py
│   └── output/
│       ├── __init__.py
│       └── my_output.py
└── tests/
    ├── test_transform.py
    └── test_output.py
```

### 9.2 Dependency Definition

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

### 9.3 Distribution Methods

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

## 10. Using in Configuration Files

Once you've implemented a plugin, you can use it in `config.toml`.

### Basic Usage Example

```toml
input_path = "data/input.parquet"
output_target = "data/output.parquet"

# TransformPlugin configuration
[[plugins]]
name = "my-transform"
module = "my_cryoflow_plugins.transform.my_transform"
enabled = true
[plugins.options]
column_name = "value"
multiplier = 2

# OutputPlugin configuration
[[plugins]]
name = "my-output"
module = "my_cryoflow_plugins.output.my_output"
enabled = true
[plugins.options]
output_path = "data/output.parquet"
```

### Chaining Multiple Plugins

```toml
input_path = "data/sales.parquet"
output_target = "data/processed.parquet"

# Filtering
[[plugins]]
name = "filter-high-value"
module = "my_plugins.transform.filter"
enabled = true
[plugins.options]
column_name = "total_amount"
threshold = 1000

# Add column
[[plugins]]
name = "add-tax"
module = "my_plugins.transform.tax_calculator"
enabled = true
[plugins.options]
amount_column = "total_amount"
tax_rate = 0.1
output_column = "tax"

# Aggregation
[[plugins]]
name = "aggregate"
module = "my_plugins.transform.aggregator"
enabled = true
[plugins.options]
group_by = ["region", "category"]
agg_columns = ["total_amount", "tax"]

# Output
[[plugins]]
name = "parquet-writer"
module = "my_plugins.output.parquet_writer"
enabled = true
[plugins.options]
output_path = "data/processed.parquet"
```

### Using Filesystem Paths

You can also specify file paths directly without installing the module as a Python package.

```toml
[[plugins]]
name = "local-plugin"
module = "./my_local_plugins/transform.py"
enabled = true
[plugins.options]
some_option = "value"

[[plugins]]
name = "absolute-path-plugin"
module = "/home/user/plugins/my_plugin.py"
enabled = true
```

---

## 11. Reference

### 11.1 Type Definitions

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

### 11.2 Base Class API

#### BasePlugin

```python
from abc import ABC, abstractmethod
from typing import Any

from cryoflow_plugin_collections.libs.polars import DataType
from cryoflow_plugin_collections.libs.returns import Result

class BasePlugin(ABC):
    def __init__(self, options: dict[str, Any]) -> None:
        """
        Args:
            options: Plugin-specific options passed from configuration file
        """
        self.options = options

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

### 11.3 Polars Method Reference

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

- ✅ Basic structure and types of plugins
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
