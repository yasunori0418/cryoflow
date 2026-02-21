"""Cryoflow core types re-export for plugin development.

Provides base classes and type definitions from cryoflow_core that are
commonly used when developing plugins.

Usage:
    from cryoflow_plugin_collections.libs.core import (
        FrameData,
        TransformPlugin,
        OutputPlugin,
    )

    class MyPlugin(TransformPlugin):
        def execute(self, df: FrameData) -> Result[FrameData, Exception]:
            # Your implementation
            pass
"""

from cryoflow_core.plugin import (
    BasePlugin,
    FrameData,
    OutputPlugin,
    TransformPlugin,
)

__all__ = [
    'FrameData',  # Type alias: LazyFrame | DataFrame
    'BasePlugin',  # Base class for all plugins
    'TransformPlugin',  # Base class for transform plugins
    'OutputPlugin',  # Base class for output plugins
]
