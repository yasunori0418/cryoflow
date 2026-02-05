"""Sample transformation plugin for cryoflow."""

import polars as pl
from returns.result import Failure, Result, Success

from cryoflow_core.plugin import FrameData, TransformPlugin


class ColumnMultiplierPlugin(TransformPlugin):
    """Multiply specified numeric column by a coefficient.

    Options:
        column_name (str): Name of the column to multiply.
        multiplier (float | int): Coefficient to multiply by.
    """

    def name(self) -> str:
        """Return the plugin identifier name."""
        return 'column_multiplier'

    def execute(self, df: FrameData) -> Result[FrameData, Exception]:
        """Transform the data frame by multiplying a column.

        Args:
            df: Input LazyFrame or DataFrame.

        Returns:
            Result containing transformed data or Exception on failure.
        """
        try:
            column_name = self.options.get('column_name')
            multiplier = self.options.get('multiplier')

            if column_name is None:
                return Failure(ValueError("Option 'column_name' is required"))
            if multiplier is None:
                return Failure(ValueError("Option 'multiplier' is required"))

            transformed = df.with_columns(
                (pl.col(column_name) * multiplier).alias(column_name)
            )
            return Success(transformed)
        except Exception as e:
            return Failure(e)

    def dry_run(self, schema: dict[str, pl.DataType]) -> Result[dict[str, pl.DataType], Exception]:
        """Validate schema and return expected output schema.

        Args:
            schema: Input schema (column_name -> DataType mapping).

        Returns:
            Result containing output schema or Exception on failure.
        """
        try:
            column_name = self.options.get('column_name')
            multiplier = self.options.get('multiplier')

            if column_name is None:
                return Failure(ValueError("Option 'column_name' is required"))
            if multiplier is None:
                return Failure(ValueError("Option 'multiplier' is required"))

            if column_name not in schema:
                return Failure(
                    ValueError(f"Column '{column_name}' not found in schema")
                )

            dtype = schema[column_name]
            # Check if dtype is a numeric type
            numeric_types = (
                pl.Int8, pl.Int16, pl.Int32, pl.Int64,
                pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64,
                pl.Float32, pl.Float64,
            )
            # Handle both type classes and instances
            if not (
                isinstance(dtype, numeric_types)
                or type(dtype) in numeric_types
            ):
                return Failure(
                    ValueError(
                        f"Column '{column_name}' has type {dtype}, "
                        "expected numeric type"
                    )
                )

            return Success(schema)
        except Exception as e:
            return Failure(e)
