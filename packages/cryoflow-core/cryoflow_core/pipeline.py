"""Data processing pipeline for cryoflow."""

import logging
from pathlib import Path
from typing import Literal

import polars as pl
from returns.result import Result, Success, Failure, safe  # noqa: F401

from cryoflow_core.plugin import FrameData, OutputPlugin, TransformPlugin

logger = logging.getLogger(__name__)


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


@safe
def extract_schema(df: FrameData) -> dict[str, pl.DataType]:
    """Extract schema from LazyFrame or DataFrame.

    Args:
        df: Input LazyFrame or DataFrame.

    Returns:
        Schema dictionary (column_name -> DataType).
    """
    if isinstance(df, pl.LazyFrame):
        return df.collect_schema()
    else:  # DataFrame
        return df.schema


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

    logger.info(f'Executing {len(plugins)} transformation plugin(s)...')

    for i, plugin in enumerate(plugins, 1):
        logger.info(f'  [{i}/{len(plugins)}] {plugin.name()}')
        result = result.bind(plugin.execute)

        if isinstance(result, Failure):
            logger.error(f'    Execution failed: {result.failure()}')
            break

    return result


def execute_dry_run_chain(
    initial_schema: Result[dict[str, pl.DataType], Exception],
    plugins: list[TransformPlugin],
) -> Result[dict[str, pl.DataType], Exception]:
    """Execute dry-run validation chain for transformation plugins.

    Args:
        initial_schema: Initial schema from input data.
        plugins: List of transformation plugins to validate.

    Returns:
        Final schema on success or Exception on failure.
    """
    result = initial_schema

    logger.info(f'Validating {len(plugins)} transformation plugin(s)...')

    for i, plugin in enumerate(plugins, 1):
        logger.info(f'  [{i}/{len(plugins)}] {plugin.name()}')

        if isinstance(result, Success):
            schema = result.unwrap()
            logger.debug(f'    Input schema: {len(schema)} columns')

        result = result.bind(plugin.dry_run)

        if isinstance(result, Success):
            schema = result.unwrap()
            logger.debug(f'    Output schema: {len(schema)} columns')
        else:
            logger.error(f'    Validation failed: {result.failure()}')
            break

    return result


def execute_output_dry_run(
    schema: Result[dict[str, pl.DataType], Exception],
    plugins: list[OutputPlugin],
) -> Result[dict[str, pl.DataType], Exception]:
    """Execute dry-run validation for output plugins.

    Each plugin receives the same schema (fan-out). Stops on first failure.

    Args:
        schema: Schema from transformation chain.
        plugins: List of output plugins to validate.

    Returns:
        Schema unchanged on success or Exception on failure.
    """
    result = schema
    for plugin in plugins:
        result = schema.bind(plugin.dry_run)
        if isinstance(result, Failure):
            break
    return result


def run_dry_run_pipeline(
    input_path: Path,
    transform_plugins: list[TransformPlugin],
    output_plugins: list[OutputPlugin],
) -> Result[dict[str, pl.DataType], Exception]:
    """Run dry-run validation pipeline without processing actual data.

    Args:
        input_path: Path to input data file.
        transform_plugins: List of transformation plugins to validate.
        output_plugins: List of output plugins to validate.

    Returns:
        Final output schema on success or Exception on failure.
    """
    initial_data = load_data(input_path)
    initial_schema = initial_data.bind(extract_schema)
    transformed_schema = execute_dry_run_chain(initial_schema, transform_plugins)
    return execute_output_dry_run(transformed_schema, output_plugins)


def execute_output(
    data: Result[FrameData, Exception],
    plugins: list[OutputPlugin],
) -> Result[None, Exception]:
    """Execute output plugins on successful data (fan-out).

    Each plugin receives the same transformed data. Stops on first failure.

    Args:
        data: Result containing data or error.
        plugins: List of output plugins to execute.

    Returns:
        Result containing None on success or Exception on failure.
    """
    result: Result[None, Exception] = Success(None)
    for plugin in plugins:
        result = data.bind(plugin.execute)
        if isinstance(result, Failure):
            break
    return result


def run_pipeline(
    input_path: Path,
    transform_plugins: list[TransformPlugin],
    output_plugins: list[OutputPlugin],
) -> Result[None, Exception]:
    """Run complete data processing pipeline.

    Args:
        input_path: Path to input data file.
        transform_plugins: List of transformation plugins to apply.
        output_plugins: List of output plugins to write results.

    Returns:
        Result containing None on success or Exception on failure.
    """
    initial_data: Result[FrameData, Exception] = load_data(input_path)
    transformed_data = execute_transform_chain(initial_data, transform_plugins)
    return execute_output(transformed_data, output_plugins)
