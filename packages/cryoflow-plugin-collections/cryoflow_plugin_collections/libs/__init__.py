"""Library re-exports for external cryoflow plugin development.

This subpackage provides convenient re-exports of commonly used libraries
for external plugin developers. By importing from this package, you can
reduce additional dependencies and ensure version compatibility.

Available modules:
- polars: Data processing with Polars
- returns: Error handling with Result monad
- core: cryoflow_core base classes and types

Usage (for external plugin developers):
    from cryoflow_plugin_collections.libs.polars import pl
    from cryoflow_plugin_collections.libs.returns.result import Result, Success, Failure
    from cryoflow_plugin_collections.libs.core import TransformPlugin, FrameData

Note: Built-in sample plugins (transform/multiplier, output/parquet_writer)
use direct imports and do not rely on this re-export mechanism.
"""

# Intentionally minimal - import specific modules as needed
