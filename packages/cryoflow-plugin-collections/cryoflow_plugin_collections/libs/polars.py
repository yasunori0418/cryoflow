"""Polars re-export for plugin development.

Provides the main polars module and commonly used types for data processing
in cryoflow plugins.

Usage:
    from cryoflow_plugin_collections.libs.polars import pl

    # Or import specific types:
    from cryoflow_plugin_collections.libs.polars import LazyFrame, DataFrame
"""

import polars as pl
from polars import DataFrame, DataType, LazyFrame

__all__ = [
    "pl",  # Main polars module
    "DataFrame",  # Eager frame type
    "LazyFrame",  # Lazy frame type (primary in cryoflow)
    "DataType",  # For dry_run schema validation
]
