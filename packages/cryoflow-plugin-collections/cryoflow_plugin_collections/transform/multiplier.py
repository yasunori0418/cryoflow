"""Sample transformation plugin for cryoflow."""

import polars as pl
from returns.result import Failure, Result, Success

from cryoflow_core.plugin import FrameData, TransformPlugin


class ColumnMultiplierPlugin(TransformPlugin):
    """Multiply specified numeric column by a coefficient.

    Options:
        column_name (str): Name of the column to multiply.
        multiplier (int | float): Coefficient to multiply by.
    """

    @property
    def name(self) -> str:
        """Return the plugin identifier name."""
        return 'column_multiplier'

    def _resolve_options(self) -> Result[tuple[str, int | float], Exception]:
        """Resolve and validate the column_name and multiplier options.

        Returns:
            Result containing the validated options on success or Exception on failure.
        """

        def to_column_name(value: object) -> Result[str, Exception]:
            if not isinstance(value, str):
                return Failure(TypeError("Option 'column_name' must be str"))
            return Success(value)

        def to_multiplier(value: object) -> Result[int | float, Exception]:
            if not isinstance(value, (int, float)):
                return Failure(TypeError("Option 'multiplier' must be int | float"))
            return Success(value)

        return (
            self.require_option('column_name')
            .bind(to_column_name)
            .bind(
                lambda column_name: (
                    self.require_option('multiplier')
                    .bind(to_multiplier)
                    .map(lambda multiplier: (column_name, multiplier))
                )
            )
        )

    def execute(self, df: FrameData) -> Result[FrameData, Exception]:
        """Transform the data frame by multiplying a column.

        Args:
            df: Input LazyFrame or DataFrame.

        Returns:
            Result containing transformed data or Exception on failure.
        """

        def multiply(options: tuple[str, int | float]) -> Result[FrameData, Exception]:
            column_name, multiplier = options
            return Success(df.with_columns((pl.col(column_name) * multiplier).alias(column_name)))

        try:
            return self._resolve_options().bind(multiply)
        except Exception as e:
            return Failure(e)

    def dry_run(self, schema: dict[str, pl.DataType]) -> Result[dict[str, pl.DataType], Exception]:
        """Validate schema and return expected output schema.

        Args:
            schema: Input schema (column_name -> DataType mapping).

        Returns:
            Result containing output schema or Exception on failure.
        """

        def validate_schema(options: tuple[str, int | float]) -> Result[dict[str, pl.DataType], Exception]:
            column_name, _ = options

            if column_name not in schema:
                return Failure(ValueError(f"Column '{column_name}' not found in schema"))

            dtype = schema[column_name]
            # Check if dtype is a numeric type
            numeric_types = (
                pl.Int8,
                pl.Int16,
                pl.Int32,
                pl.Int64,
                pl.UInt8,
                pl.UInt16,
                pl.UInt32,
                pl.UInt64,
                pl.Float32,
                pl.Float64,
            )
            # Handle both type classes and instances
            if not (isinstance(dtype, numeric_types) or type(dtype) in numeric_types):
                return Failure(ValueError(f"Column '{column_name}' has type {dtype}, expected numeric type"))

            return Success(schema)

        try:
            return self._resolve_options().bind(validate_schema)
        except Exception as e:
            return Failure(e)
