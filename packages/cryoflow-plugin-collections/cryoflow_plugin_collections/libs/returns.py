"""Returns library re-export for plugin development.

Provides complete returns.result API re-export for external plugin developers.
This module transparently re-exports all public APIs from returns.result,
ensuring version compatibility and reducing dependency management overhead.

Usage:
    # Import individual types/functions
    from cryoflow_plugin_collections.libs.returns import Result, Success, Failure, safe

    # Import ResultE alias (Result[T, Exception])
    from cryoflow_plugin_collections.libs.returns import ResultE

    # Import decorators and utilities
    from cryoflow_plugin_collections.libs.returns import safe, attempt

Example:
    from cryoflow_plugin_collections.libs.returns import Result, Success, Failure, safe

    @safe
    def process() -> Result[str, Exception]:
        return Success("value")

All imports provide full type hints and IDE autocomplete support.
"""

from returns.result import *  # noqa: F403, F401

# Import returns.result module to build __all__, but don't re-export it
# (returns.result.result conflicts with module name)
import returns.result as _result_module

# Build __all__ dynamically to include all returns.result public APIs
__all__ = [name for name in dir(_result_module) if not name.startswith("_")]

# Clean up temporary reference
del _result_module
