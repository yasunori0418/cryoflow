"""Polars re-export for plugin development.

Provides complete polars API re-export for external plugin developers.
This module transparently re-exports all 228+ public APIs from polars,
ensuring version compatibility and reducing dependency management overhead.

Usage:
    # Import as module (enables pl.col(), pl.DataFrame(), etc.)
    from cryoflow_plugin_collections.libs import polars as pl
    pl.col("name")

    # Import the polars module object
    from cryoflow_plugin_collections.libs.polars import pl
    pl.col("name")

    # Import individual functions/types
    from cryoflow_plugin_collections.libs.polars import col, lit, when, DataFrame, LazyFrame

All imports provide full type hints and IDE autocomplete support.
"""

import polars as pl
from polars import *  # noqa: F403, F401 # pyright: ignore[reportWildcardImportFromLibrary]

# Build __all__ dynamically to include all polars public APIs plus 'pl'
__all__ = [name for name in dir(pl) if not name.startswith('_')]  # pyright: ignore[reportUnsupportedDunderAll]
