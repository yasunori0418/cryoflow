"""Returns library re-export for plugin development.

Provides Result monad utilities for error handling in cryoflow plugins.
All plugin execute methods return Result[T, Exception].

Usage:
    from cryoflow_plugin_collections.libs.returns import Result, Success, Failure

    def process() -> Result[str, Exception]:
        try:
            return Success("value")
        except Exception as e:
            return Failure(e)
"""

from returns.result import Failure, Result, Success

__all__ = [
    "Result",  # Result type for type hints
    "Success",  # Success wrapper
    "Failure",  # Failure wrapper
]
