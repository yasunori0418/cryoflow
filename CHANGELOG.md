# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.3] - 2026-02-17

### Added

- **Complete polars API re-export** (`cryoflow-plugin-collections`):
  - Re-export all 228+ public APIs from polars using wildcard import
  - Support for 3 import patterns:
    1. Module import: `from libs import polars as pl; pl.col()`
    2. Object import: `from libs.polars import pl; pl.col()`
    3. Individual imports: `from libs.polars import col, lit, when`
  - Dynamic `__all__` generation for automatic tracking of polars updates
  - Zero maintenance overhead and zero runtime overhead
  - Full type safety and IDE autocomplete support

- **Complete returns library re-export** (`cryoflow-plugin-collections`):
  - Re-export 146+ unique public APIs from 13 major returns modules
  - Newly available containers and utilities:
    - `Maybe` monad for optional values (`Some`, `Nothing`)
    - `IO` containers for side effect management (`IO`, `IOResult`)
    - `Future` for async operations (`Future`, `FutureResult`)
    - `Context` for dependency injection (`RequiresContext`)
    - Pipeline utilities (`flow`, `pipe`)
    - Pointfree operations (`bind`, `map`, `alt`, `lash`)
    - Curry/partial application utilities
    - Converters and methods for container transformations
  - Support for individual imports: `from libs.returns import Maybe, IO, flow`
  - Full functional programming toolkit for plugin developers

### Changed

- **Improved `__all__` construction** (`cryoflow-plugin-collections`):
  - Refactored returns module to use single assignment pattern
  - Replaced destructive extend/reassign with list comprehension and temporary variable
  - Better static analysis compatibility (reduced Pyright warnings)

### Tests

- Added comprehensive tests for polars re-export (4 new test cases)
- Added comprehensive tests for returns re-export (4 new test cases)
- All 44 tests passing with full backward compatibility

## [0.1.0] - 2025-02-12

### Added

- **Path resolution system**: All file paths in configuration are now resolved relative to the config file's directory
  - `config.py`: Added `_resolve_path_relative_to_config()` helper function
  - `BasePlugin`: Added `resolve_path()` method for consistent path resolution across plugins
  - Comprehensive E2E tests for relative path resolution

### Changed

- **BREAKING CHANGE**: `BasePlugin.__init__()` now requires `config_dir` parameter (no longer optional)
  - Remove backward compatibility fallback to eliminate technical debt
  - All plugins must explicitly receive `config_dir` during instantiation
- **BREAKING CHANGE**: Relative paths in `input_path` are now resolved relative to config file directory instead of current working directory
- **BREAKING CHANGE**: Plugin option paths are resolved relative to config file directory
- Updated `ParquetWriterPlugin` to use `resolve_path()` for output paths
- Updated all example configurations to use relative paths

### Documentation

- Added comprehensive path resolution behavior section to `docs/spec.md` and `docs/spec_ja.md`
- Updated `README.md` and `README_ja.md` with path resolution guidelines
- Updated plugin development guides (`docs/plugin_development.md`, `docs/plugin_development_ja.md`) with new API

### Migration Guide

#### For Configuration Files

Update relative paths to be relative to the config file location:

```toml
# Before (0.0.x): paths relative to current working directory
input_path = "examples/data/input.parquet"

# After (0.1.0): paths relative to config file directory
# If config.toml is in project root:
input_path = "examples/data/input.parquet"  # Same if running from project root

# If config.toml is in config/:
input_path = "../examples/data/input.parquet"  # OR use absolute path
```

#### For Plugin Development

Update plugin constructors to accept `config_dir`:

```python
# Before (0.0.x)
class MyPlugin(OutputPlugin):
    def execute(self, df):
        output_path = Path(self.options.get('output_path'))
        # ...

# After (0.1.0)
class MyPlugin(OutputPlugin):
    def execute(self, df):
        output_path = self.resolve_path(self.options.get('output_path'))
        # ...
```

## [0.0.4] - 2025-02-11

### Changed

- Remove unused `output_target` configuration field

## [0.0.3] - 2025-02-11

Initial working release with core functionality.
