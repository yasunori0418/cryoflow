"""Cryoflow core types re-export for plugin development.

Provides base classes and type definitions from cryoflow_core that are
commonly used when developing plugins.

Usage:
    from cryoflow_plugin_collections.libs.core import (
        FrameData,
        InputPlugin,
        TransformPlugin,
        OutputPlugin,
    )

    class MyPlugin(TransformPlugin):
        def execute(self, df: FrameData) -> Result[FrameData, Exception]:
            # Your implementation
            pass
"""

from cryoflow_core.plugin import (
    FrameData as FrameData,
    InputPlugin as InputPlugin,
    OutputPlugin as OutputPlugin,
    TransformPlugin as TransformPlugin,
)

__all__ = [
    'FrameData',  # Type alias: LazyFrame | DataFrame
    'InputPlugin',  # Base class for input plugins
    'TransformPlugin',  # Base class for transform plugins
    'OutputPlugin',  # Base class for output plugins
]
