"""Returns library re-export for plugin development.

Provides complete returns library API re-export for external plugin developers.
This module transparently re-exports all 230+ public APIs from returns,
ensuring version compatibility and reducing dependency management overhead.

The returns library provides type-safe functional programming primitives for
Python, including containers for error handling, optional values, IO effects,
async operations, and context management.

Usage:
    # Result monad (error handling)
    from cryoflow_plugin_collections.libs.returns import Result, Success, Failure, safe

    # Maybe monad (optional values)
    from cryoflow_plugin_collections.libs.returns import Maybe, Some, Nothing

    # IO containers (side effects)
    from cryoflow_plugin_collections.libs.returns import IO, IOResult

    # Pipeline utilities (function composition)
    from cryoflow_plugin_collections.libs.returns import flow, pipe

    # Pointfree operations
    from cryoflow_plugin_collections.libs.returns import bind, map

Examples:
    # Error handling with Result
    from cryoflow_plugin_collections.libs.returns import Result, Success, Failure, safe

    @safe
    def divide(a: int, b: int) -> float:
        return a / b

    result = divide(10, 2)  # Success(5.0)
    error = divide(10, 0)   # Failure(ZeroDivisionError(...))

    # Optional values with Maybe
    from cryoflow_plugin_collections.libs.returns import Maybe, Some, Nothing

    def find_user(id: int) -> Maybe[str]:
        return Some("Alice") if id == 1 else Nothing

    # Function composition
    from cryoflow_plugin_collections.libs.returns import flow, Result

    process = flow(
        parse_input,
        validate_data,
        transform_data,
    )

All imports provide full type hints and IDE autocomplete support.

Re-exported modules:
    - result: Result, Success, Failure, ResultE, safe, etc.
    - maybe: Maybe, Some, Nothing, etc.
    - io: IO, IOResult, impure, etc.
    - future: Future, FutureResult, etc.
    - context: Context, RequiresContext, etc.
    - pipeline: flow, pipe, managed
    - pointfree: bind, map, alt, lash, etc.
    - iterables: Fold, fold, etc.
    - curry: curry, partial, etc.
    - functions: identity, tap, raise_exception, etc.
    - converters: coalesce_result, flatten, etc.
    - methods: cond, not_
    - primitives: Immutable, interfaces
"""

# Re-export all public APIs from major returns modules
from returns.result import *  # noqa: F403, F401 # pyright: ignore[reportWildcardImportFromLibrary]
from returns.maybe import *  # noqa: F403, F401 # pyright: ignore[reportWildcardImportFromLibrary]
from returns.io import *  # noqa: F403, F401 # pyright: ignore[reportWildcardImportFromLibrary]
from returns.future import *  # noqa: F403, F401 # pyright: ignore[reportWildcardImportFromLibrary]
from returns.context import *  # noqa: F403, F401 # pyright: ignore[reportWildcardImportFromLibrary]
from returns.pipeline import *  # noqa: F403, F401 # pyright: ignore[reportWildcardImportFromLibrary]
from returns.pointfree import *  # noqa: F403, F401 # pyright: ignore[reportWildcardImportFromLibrary]
from returns.iterables import *  # noqa: F403, F401 # pyright: ignore[reportWildcardImportFromLibrary]
from returns.curry import *  # noqa: F403, F401 # pyright: ignore[reportWildcardImportFromLibrary]
from returns.functions import *  # noqa: F403, F401 # pyright: ignore[reportWildcardImportFromLibrary]
from returns.converters import *  # noqa: F403, F401 # pyright: ignore[reportWildcardImportFromLibrary]
from returns.methods import *  # noqa: F403, F401 # pyright: ignore[reportWildcardImportFromLibrary]
from returns.primitives import *  # noqa: F403, F401 # pyright: ignore[reportWildcardImportFromLibrary]

# Import module objects for building __all__ and optional re-export
from returns import (
    result,
    maybe,
    io,
    future,
    context,
    pipeline,
    pointfree,
    iterables,
    curry,
    functions,
    converters,
    methods,
    primitives,
)

# Build __all__ dynamically from all re-exported modules
_modules = [
    result,
    maybe,
    io,
    future,
    context,
    pipeline,
    pointfree,
    iterables,
    curry,
    functions,
    converters,
    methods,
    primitives,
]

# Build __all__ from all module exports with deduplication
_all_exports = [name for _mod in _modules for name in dir(_mod) if not name.startswith('_')]

# Remove duplicates while preserving order, then assign to __all__
__all__ = list(dict.fromkeys(_all_exports))  # pyright: ignore[reportUnsupportedDunderAll]

# Clean up temporary references
del _modules, _all_exports
