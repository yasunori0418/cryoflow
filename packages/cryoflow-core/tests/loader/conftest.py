"""Fixtures and constants for loader tests."""

import sys
from pathlib import Path

import pytest


INPUT_PLUGIN_SOURCE = """\
from typing import Any
import polars as pl
from returns.result import Success, Result
from cryoflow_core.plugin import InputPlugin, FrameData


class MyInputPlugin(InputPlugin):
    def name(self) -> str:
        return "my_input"

    def execute(self) -> Result[FrameData, Exception]:
        return Success(pl.LazyFrame({'a': [1, 2, 3]}))

    def dry_run(self) -> Result[dict[str, pl.DataType], Exception]:
        return Success({'a': pl.Int64})
"""

TRANSFORM_PLUGIN_SOURCE = """\
from typing import Any
import polars as pl
from returns.result import Success, Result
from cryoflow_core.plugin import TransformPlugin, FrameData


class MyTransformPlugin(TransformPlugin):
    def name(self) -> str:
        return "my_transform"

    def execute(self, df: FrameData) -> Result[FrameData, Exception]:
        return Success(df)

    def dry_run(
        self, schema: dict[str, pl.DataType]
    ) -> Result[dict[str, pl.DataType], Exception]:
        return Success(schema)
"""

OUTPUT_PLUGIN_SOURCE = """\
from typing import Any
import polars as pl
from returns.result import Success, Result
from cryoflow_core.plugin import OutputPlugin, FrameData


class MyOutputPlugin(OutputPlugin):
    def name(self) -> str:
        return "my_output"

    def execute(self, df: FrameData) -> Result[None, Exception]:
        return Success(None)

    def dry_run(
        self, schema: dict[str, pl.DataType]
    ) -> Result[dict[str, pl.DataType], Exception]:
        return Success(schema)
"""

BOTH_PLUGINS_SOURCE = TRANSFORM_PLUGIN_SOURCE + '\n' + OUTPUT_PLUGIN_SOURCE

SYNTAX_ERROR_SOURCE = """\
def broken(
    # missing closing paren
"""

EMPTY_MODULE_SOURCE = """\
# No plugins here
x = 42
"""


@pytest.fixture()
def input_plugin_py_file(tmp_path: Path):
    """Create a .py file with an InputPlugin implementation."""
    p = tmp_path / 'my_input_plugin.py'
    p.write_text(INPUT_PLUGIN_SOURCE)
    return p


@pytest.fixture()
def plugin_py_file(tmp_path: Path):
    """Create a .py file with a TransformPlugin implementation."""
    p = tmp_path / 'my_plugin.py'
    p.write_text(TRANSFORM_PLUGIN_SOURCE)
    return p


@pytest.fixture()
def output_plugin_py_file(tmp_path: Path):
    """Create a .py file with an OutputPlugin implementation."""
    p = tmp_path / 'my_output_plugin.py'
    p.write_text(OUTPUT_PLUGIN_SOURCE)
    return p


@pytest.fixture()
def both_plugins_py_file(tmp_path: Path):
    """Create a .py file with both Transform and Output plugins."""
    p = tmp_path / 'both_plugins.py'
    p.write_text(BOTH_PLUGINS_SOURCE)
    return p


@pytest.fixture(autouse=True)
def cleanup_sys_modules():
    """Remove cryoflow_plugin_* entries from sys.modules after each test."""
    yield
    to_remove = [k for k in sys.modules if k.startswith('cryoflow_plugin_')]
    for k in to_remove:
        del sys.modules[k]
