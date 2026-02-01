# Implementation Plan

The project is divided into 4 phases for staged implementation.

## Phase 1: Core Framework Construction (CLI & Config) ✅ Completed

**Goal**: Verify that configuration files can be loaded and commands are launched via Typer.

### 1-1. Project Setup

- monorepo structure with uv workspace (`cryoflow-core`, `cryoflow-sample-plugin`)
- Python 3.14 target
- Development environment via Nix flake

### 1-2. Config Implementation (`cryoflow_core/config.py`)

- `PluginConfig`: Pydantic model with name, module, enabled(=True), options(=dict)
- `CryoflowConfig`: input_path(Path), output_target(str), plugins(list[PluginConfig])
- `ConfigLoadError`: Exception wrapping file not found / TOML parse error / validation error
- `get_default_config_path()`: Returns `xdg_config_home() / "cryoflow" / "config.toml"`
- `load_config(config_path)`: Load TOML → Pydantic validation → return `CryoflowConfig`
- Uses Python 3.14 stdlib `tomllib` (no external TOML dependency needed)

### 1-3. Typer Implementation (`cryoflow_core/cli.py`)

- `app = typer.Typer(no_args_is_help=True)` + `@app.callback()` to establish subcommand structure
- `cryoflow run` command: `-c / --config` option (`exists=True, dir_okay=False, resolve_path=True`)
- Mock implementation at this stage (display loaded configuration only)
- `ConfigLoadError` → stderr output + exit code 1

### 1-4. Entry Point

- Register `[project.scripts] cryoflow = "cryoflow_core.cli:app"` in root `pyproject.toml`

### 1-5. Sample Configuration

- Create sample configuration file at `examples/config.toml`

### Error Handling Design

| Issue | Detection Point | User Display |
|------|----------|------------|
| File not found (XDG default) | `load_config()` → `ConfigLoadError` | `Config file not found: ~/.config/cryoflow/config.toml` |
| File not found (`--config` specified) | Typer `exists=True` | Typer built-in error message |
| TOML syntax error | `load_config()` → `ConfigLoadError` | `Failed to parse TOML config: ...` |
| Pydantic validation | `load_config()` → `ConfigLoadError` | `Config validation failed: ...` |

---

## Phase 2: Plugin Mechanism Implementation (Pluggy & ABC) ✅ Completed

**Goal**: Load classes defined in external files and call their methods.

### 2-1. ABC Base Class Implementation (`cryoflow_core/plugin.py`)

- Type alias: `FrameData = Union[pl.LazyFrame, pl.DataFrame]`
- `BasePlugin(ABC)`: Define `__init__(options)`, `name()`, `dry_run(schema)`
- `TransformPlugin(BasePlugin)`: `execute(df) -> Result[FrameData, Exception]`
- `OutputPlugin(BasePlugin)`: `execute(df) -> Result[None, Exception]`

### 2-2. HookSpec Definition (`cryoflow_core/hookspecs.py`)

- Define hookspec with `pluggy.HookspecMarker("cryoflow")`
- `register_transform_plugins() -> list[TransformPlugin]`
- `register_output_plugins() -> list[OutputPlugin]`

### 2-3. Plugin Loader (`cryoflow_core/loader.py`)

- Dynamic import via `importlib` from module path string in configuration
- Instantiate classes and register with `PluginManager`
- Error handling for load failures

### 2-4. Test Plugin Creation

- Implement Identity plugin (no-op transformation) in `cryoflow-sample-plugin`
- Test plugin loading, registration, and execution

### Additional Dependencies

- `cryoflow-core`: `pluggy`, `returns`
- `cryoflow-sample-plugin`: `cryoflow-core`, `polars`

---

## Phase 3: Data Processing Pipeline Implementation (Polars & Returns) ✅ Completed

**Goal**: Enable reading Parquet files, processing, and saving.

### 3-1. LazyFrame Integration (`cryoflow_core/pipeline.py`)

- Data loading via `pl.scan_parquet` / `pl.scan_ipc`
- Automatic format detection based on input path extension

### 3-2. Pipeline Runner

- Chain plugins using `returns` `flow` / `bind`
- Execute `TransformPlugin.execute` sequentially, building computation graph (LazyFrame)
- Immediately halt processing if `Failure` is returned

### 3-3. Output Implementation

- Evaluate results in `OutputPlugin.execute` with `collect()` / `sink_parquet()` etc.
- Switch `cli.py` `run` command from mock to actual pipeline execution

### 3-4. Integration Testing

- End-to-end testing with sample Parquet files covering input→transformation→output

---

## Phase 4: Dry-Run and Robustness ✅ Completed

**Goal**: Perform schema validation without flowing actual data and complete error handling.

### 4-1. Dry-Run Implementation

- Add `cryoflow check` command (or `run --dry-run`)
- Chain `dry_run` methods of each plugin and display final output schema

### 4-2. Error Handling Enhancement

- Use `returns` `safe` decorator to convert unexpected exceptions to `Failure`
- Unify error wrapping at plugin boundaries

### 4-3. Logging

- Establish logging output for processing steps

---

## Implemented Pipeline Verification

Phase 3 completed. The following has been implemented:

### 3-1. `pipeline.py` - Core Pipeline Implementation
- `_detect_format()`: Auto-detect Parquet/IPC format from file extension
- `load_data()`: Auto-convert exceptions to `Result` with `@safe` decorator
- `execute_transform_chain()`: Chain plugin execution with `returns.Result.bind()`
- `execute_output()`: Pass transformed data to output plugins
- `run_pipeline()`: Unified pipeline for load→transform→output

### 3-2. Sample Plugin Implementation
- `ColumnMultiplierPlugin`: Multiply specified column by coefficient (supports LazyFrame computation graph)
- `ParquetWriterPlugin`: Output to Parquet file (streaming write with `sink_parquet()`)

### 3-3. Test Coverage
- `test_pipeline.py`: Unit tests for pipeline functions (20 tests)
- `test_transform.py`: Unit tests for transform plugin (21 tests)
- `test_output.py`: Unit tests for output plugin (9 tests)
- `test_e2e.py`: E2E integration tests (4 tests)
- **Total**: All 140 tests pass

### 3-4. CLI Integration
- Extended `cli.py` `run` command for pipeline execution
- Output plugin validation logic (single plugin support)
- Success/Failure processing and detailed error message display

### 3-5. Live Operation Verification
```bash
python -c "from cryoflow_core.cli import app; app(['run', '-c', 'examples/config.toml'])"
```
✅ Working correctly: Parquet → (total_amount × 2) → Parquet

---

## Next Action

Phase 3 completed. Ready to proceed to **Phase 4: Dry-Run and Robustness**.
- Implement `cryoflow check` command
- Strengthen schema validation
- Complete logging system
