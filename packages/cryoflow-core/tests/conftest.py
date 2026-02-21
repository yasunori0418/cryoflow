"""Shared fixtures and helpers for cryoflow-core tests."""

from pathlib import Path
from typing import Any

import polars as pl
import pytest
from returns.result import Failure, Success

from cryoflow_core.plugin import (
    DEFAULT_LABEL,
    FrameData,
    InputPlugin,
    OutputPlugin,
    TransformPlugin,
)


# ---------------------------------------------------------------------------
# Concrete plugin classes for testing (ABC cannot be instantiated directly)
# ---------------------------------------------------------------------------


class DummyInputPlugin(InputPlugin):
    """Input plugin that returns a fixed LazyFrame."""

    def name(self) -> str:
        return 'dummy_input'

    def execute(self) -> Success[FrameData]:
        return Success(pl.LazyFrame({'a': [1, 2, 3], 'b': ['x', 'y', 'z']}))

    def dry_run(self) -> Success[dict[str, pl.DataType]]:
        return Success({'a': pl.Int64(), 'b': pl.String()})


class DummyTransformPlugin(TransformPlugin):
    """Identity transform plugin that returns input unchanged."""

    def name(self) -> str:
        return 'dummy_transform'

    def execute(self, df: FrameData) -> Success[FrameData]:
        return Success(df)

    def dry_run(self, schema: dict[str, pl.DataType]) -> Success[dict[str, pl.DataType]]:
        return Success(schema)


class DummyOutputPlugin(OutputPlugin):
    """No-op output plugin."""

    def name(self) -> str:
        return 'dummy_output'

    def execute(self, df: FrameData) -> Success[None]:
        return Success(None)

    def dry_run(self, schema: dict[str, pl.DataType]) -> Success[dict[str, pl.DataType]]:
        return Success(schema)


class FailingTransformPlugin(TransformPlugin):
    """Transform plugin that always fails."""

    def name(self) -> str:
        return 'failing_transform'

    def execute(self, df: FrameData) -> Failure[Exception]:
        return Failure(ValueError('intentional failure'))

    def dry_run(self, schema: dict[str, pl.DataType]) -> Failure[Exception]:
        return Failure(ValueError('intentional dry_run failure'))


class BrokenInitPlugin(TransformPlugin):
    """Plugin that raises during __init__."""

    def __init__(self, options: dict[str, Any], config_dir: Path, label: str = DEFAULT_LABEL) -> None:
        raise RuntimeError('broken init')

    def name(self) -> str:
        return 'broken_init'

    def execute(self, df: FrameData) -> Success[FrameData]:
        return Success(df)

    def dry_run(self, schema: dict[str, pl.DataType]) -> Success[dict[str, pl.DataType]]:
        return Success(schema)


# ---------------------------------------------------------------------------
# TOML string constants
# ---------------------------------------------------------------------------

VALID_TOML = """\
output_plugins = []

[[input_plugins]]
name = "my_input"
module = "my_input_mod"
enabled = true

[[transform_plugins]]
name = "my_plugin"
module = "my_module"
enabled = true

[transform_plugins.options]
threshold = 42
"""

MINIMAL_TOML = """\
input_plugins = []
transform_plugins = []
output_plugins = []
"""

INVALID_TOML_SYNTAX = """\
input_plugins = /invalid  # missing brackets
transform_plugins = []
"""

MISSING_FIELDS_TOML = """\
transform_plugins = []
"""

MULTI_PLUGIN_TOML = """\
[[input_plugins]]
name = "input_a"
module = "input_mod_a"
label = "sales"

[[transform_plugins]]
name = "plugin_a"
module = "mod_a"

[[transform_plugins]]
name = "plugin_b"
module = "mod_b"
enabled = false

[[output_plugins]]
name = "plugin_c"
module = "mod_c"

[output_plugins.options]
key = "value"
"""

# ---------------------------------------------------------------------------
# Config file fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def valid_config_file(tmp_path):
    """Create a temporary valid TOML config file."""
    p = tmp_path / 'config.toml'
    p.write_text(VALID_TOML)
    return p


@pytest.fixture()
def minimal_config_file(tmp_path):
    """Create a temporary minimal TOML config file."""
    p = tmp_path / 'config.toml'
    p.write_text(MINIMAL_TOML)
    return p


@pytest.fixture()
def invalid_syntax_config_file(tmp_path):
    """Create a temporary TOML config file with syntax errors."""
    p = tmp_path / 'config.toml'
    p.write_text(INVALID_TOML_SYNTAX)
    return p


@pytest.fixture()
def missing_fields_config_file(tmp_path):
    """Create a temporary TOML config file with missing required fields."""
    p = tmp_path / 'config.toml'
    p.write_text(MISSING_FIELDS_TOML)
    return p


@pytest.fixture()
def multi_plugin_config_file(tmp_path):
    """Create a temporary TOML config file with multiple plugins."""
    p = tmp_path / 'config.toml'
    p.write_text(MULTI_PLUGIN_TOML)
    return p


# ---------------------------------------------------------------------------
# Polars fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_lazyframe():
    """Return a sample Polars LazyFrame."""
    return pl.LazyFrame({'a': [1, 2, 3], 'b': ['x', 'y', 'z']})


@pytest.fixture()
def sample_dataframe():
    """Return a sample Polars DataFrame."""
    return pl.DataFrame({'a': [1, 2, 3], 'b': ['x', 'y', 'z']})
