"""Data processing pipeline for cryoflow."""

from pathlib import Path
from typing import Literal

import polars as pl
from returns.result import Result, safe

from cryoflow_core.plugin import FrameData, OutputPlugin, TransformPlugin


def _detect_format(path: Path) -> Literal['parquet', 'ipc'] | None:
    """Detect file format from file extension.

    Args:
        path: Path to the data file.

    Returns:
        Format name ('parquet' or 'ipc') or None if unknown.
    """
    suffix = path.suffix.lower()
    if suffix == '.parquet':
        return 'parquet'
    if suffix in ('.ipc', '.arrow'):
        return 'ipc'
    return None


@safe
def load_data(input_path: Path) -> pl.LazyFrame:
    """Load data from Parquet or IPC format with lazy evaluation.

    Args:
        input_path: Path to the data file.

    Returns:
        Result containing LazyFrame on success or Exception on failure.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file format is not supported.
    """
    if not input_path.exists():
        raise FileNotFoundError(f'Input file not found: {input_path}')

    fmt = _detect_format(input_path)
    if fmt is None:
        raise ValueError(f'Unsupported file format: {input_path.suffix}')

    if fmt == 'parquet':
        return pl.scan_parquet(input_path)
    else:  # fmt == 'ipc'
        return pl.scan_ipc(input_path)


def execute_transform_chain(
    initial_data: Result[FrameData, Exception],
    plugins: list[TransformPlugin],
) -> Result[FrameData, Exception]:
    """Execute transformation plugin chain using railway-oriented programming.

    Args:
        initial_data: Initial result containing data or error.
        plugins: List of transformation plugins to apply in order.

    Returns:
        Result containing transformed data on success or Exception on failure.
    """
    result = initial_data
    for plugin in plugins:
        result = result.bind(plugin.execute)
    return result


def execute_output(
    data: Result[FrameData, Exception],
    plugin: OutputPlugin,
) -> Result[None, Exception]:
    """Execute output plugin on successful data.

    Args:
        data: Result containing data or error.
        plugin: Output plugin to execute.

    Returns:
        Result containing None on success or Exception on failure.
    """
    return data.bind(plugin.execute)


def run_pipeline(
    input_path: Path,
    transform_plugins: list[TransformPlugin],
    output_plugin: OutputPlugin,
) -> Result[None, Exception]:
    """Run complete data processing pipeline.

    Args:
        input_path: Path to input data file.
        transform_plugins: List of transformation plugins to apply.
        output_plugin: Output plugin to write results.

    Returns:
        Result containing None on success or Exception on failure.
    """
    initial_data: Result[FrameData, Exception] = load_data(input_path)
    transformed_data = execute_transform_chain(initial_data, transform_plugins)
    return execute_output(transformed_data, output_plugin)
