"""cryoflow plugin collections.

This package provides:
1. Built-in sample plugins for cryoflow
   - ColumnMultiplierPlugin: Multiply numeric columns by a factor
   - ParquetWriterPlugin: Write data to Parquet files

2. Library re-exports for external plugin development (libs subpackage)
   - Reduces additional dependencies for external plugin developers
   - Ensures version compatibility with cryoflow-core

For External Plugin Developers:
    # Recommended: Import from libs to reduce dependencies
    from cryoflow_plugin_collections.libs.polars import pl
    from cryoflow_plugin_collections.libs.returns import Result, Success, Failure
    from cryoflow_plugin_collections.libs.core import TransformPlugin, FrameData

    class MyCustomPlugin(TransformPlugin):
        def execute(self, df: FrameData) -> Result[FrameData, Exception]:
            # Your implementation
            pass

For Built-in Sample Plugins:
    # Sample plugins use direct imports (internal implementation detail)
    import polars as pl
    from returns.result import Result, Success, Failure
    from cryoflow_core.plugin import TransformPlugin, FrameData
"""

from cryoflow_plugin_collections.output import ParquetWriterPlugin
from cryoflow_plugin_collections.transform import ColumnMultiplierPlugin

__all__ = ['ColumnMultiplierPlugin', 'ParquetWriterPlugin']
