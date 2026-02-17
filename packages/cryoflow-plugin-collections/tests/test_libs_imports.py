"""Tests for library re-exports in libs subpackage."""


def test_polars_reexport():
    """Test polars re-export works correctly."""
    from cryoflow_plugin_collections.libs.polars import DataFrame, LazyFrame, pl

    # Verify imports are accessible
    assert pl is not None
    assert LazyFrame is not None
    assert DataFrame is not None

    # Verify actual usage
    df = pl.DataFrame({"a": [1, 2, 3]})
    assert isinstance(df, DataFrame)


def test_returns_reexport():
    """Test returns re-export works correctly."""
    from cryoflow_plugin_collections.libs.returns import Failure, Result, Success

    # Verify Success works
    result: Result[int, str] = Success(42)
    assert result.unwrap() == 42

    # Verify Failure works
    error_result: Result[int, str] = Failure("error")
    assert error_result.failure()


def test_returns_individual_imports():
    """Test importing individual types/functions from returns re-export."""
    from cryoflow_plugin_collections.libs.returns import (
        Failure,
        Result,
        ResultE,
        Success,
        safe,
    )

    # Verify all imports are accessible
    assert Result is not None
    assert Success is not None
    assert Failure is not None
    assert ResultE is not None
    assert callable(safe)

    # Test actual usage
    result: Result[int, str] = Success(42)
    assert result.unwrap() == 42

    error_result: Result[int, str] = Failure("error")
    assert error_result.failure()

    # Test safe decorator
    @safe
    def may_fail(x: int) -> int:
        if x < 0:
            raise ValueError("negative")
        return x * 2

    success_result = may_fail(5)
    assert success_result.unwrap() == 10

    failure_result = may_fail(-1)
    assert failure_result.failure()


def test_returns_extended_apis():
    """Test extended returns APIs are available."""
    from cryoflow_plugin_collections.libs.returns import (
        IO,
        Maybe,
        Nothing,
        Some,
        bind,
        flow,
        pipe,
    )

    # Test Maybe monad
    some_value: Maybe[int] = Some(42)
    assert some_value.unwrap() == 42

    # Nothing is a singleton value, not a container instance
    assert Nothing is not None

    # Test pipeline utilities
    def add_one(x: int) -> int:
        return x + 1

    def multiply_two(x: int) -> int:
        return x * 2

    # Test flow (applies functions left-to-right starting from a value)
    result_flow = flow(5, add_one, multiply_two)
    assert result_flow == 12

    # Test pipe (composes functions into a new function)
    composed_fn = pipe(add_one, multiply_two)
    assert callable(composed_fn)
    assert composed_fn(5) == 12

    # Test IO container
    assert IO is not None
    assert callable(bind)


def test_returns_complete_api_export():
    """Test that all returns major module APIs are exported."""
    from cryoflow_plugin_collections.libs import returns as returns_reexport

    # Verify we have a substantial number of APIs re-exported
    # (returns has 140+ unique public APIs across all modules after deduplication)
    assert len(returns_reexport.__all__) > 140

    # Verify major container types are present
    assert "Result" in returns_reexport.__all__
    assert "Success" in returns_reexport.__all__
    assert "Failure" in returns_reexport.__all__
    assert "Maybe" in returns_reexport.__all__
    assert "Some" in returns_reexport.__all__
    assert "Nothing" in returns_reexport.__all__
    assert "IO" in returns_reexport.__all__
    assert "Future" in returns_reexport.__all__

    # Verify utilities are present
    assert "flow" in returns_reexport.__all__
    assert "pipe" in returns_reexport.__all__
    assert "bind" in returns_reexport.__all__
    assert "safe" in returns_reexport.__all__


def test_returns_type_identity():
    """Test that re-exported objects are identical to originals."""
    import returns.result
    from cryoflow_plugin_collections.libs.returns import (
        Failure,
        Result,
        Success,
        safe,
    )

    # Verify objects are identical (not copies)
    assert Result is returns.result.Result
    assert Success is returns.result.Success
    assert Failure is returns.result.Failure
    assert safe is returns.result.safe


def test_core_reexport():
    """Test core re-export works correctly."""
    from cryoflow_plugin_collections.libs.core import (
        FrameData,
        OutputPlugin,
        TransformPlugin,
    )

    # Verify imports are accessible
    assert FrameData is not None
    assert TransformPlugin is not None
    assert OutputPlugin is not None


def test_backward_compatibility_direct_imports():
    """Verify existing direct import pattern still works."""
    import polars as pl
    from returns.result import Success

    from cryoflow_core.plugin import TransformPlugin

    # All should be accessible
    assert pl is not None
    assert Success is not None
    assert TransformPlugin is not None


def test_polars_module_import():
    """Test importing polars as module enables all APIs."""
    from cryoflow_plugin_collections.libs import polars as pl

    # Pattern 1: Module-level API access
    assert hasattr(pl, "col")
    assert hasattr(pl, "lit")
    assert hasattr(pl, "when")

    # Verify actual usage
    expr = pl.col("name")
    assert expr is not None

    df = pl.DataFrame({"x": [1, 2, 3]})
    assert isinstance(df, pl.DataFrame)


def test_polars_individual_imports():
    """Test importing individual functions from polars re-export."""
    from cryoflow_plugin_collections.libs.polars import (
        DataFrame,
        LazyFrame,
        col,
        concat,
        lit,
        scan_parquet,
        when,
    )

    # Verify all imports are callable/classes
    assert callable(col)
    assert callable(lit)
    assert callable(when)
    assert callable(concat)
    assert callable(scan_parquet)

    # Test actual usage
    expr = col("name")
    assert expr is not None

    df = DataFrame({"a": [1, 2, 3]})
    assert isinstance(df, DataFrame)

    lf = LazyFrame({"b": ["x", "y", "z"]})
    assert isinstance(lf, LazyFrame)


def test_polars_complete_api_export():
    """Test that all polars public APIs are exported."""
    import polars
    from cryoflow_plugin_collections.libs import polars as polars_reexport

    # Get all public APIs from original polars
    original_apis = {name for name in dir(polars) if not name.startswith("_")}

    # Get all exports from re-export module
    reexport_apis = set(polars_reexport.__all__)

    # Verify all original APIs are re-exported (+1 for 'pl')
    assert original_apis.issubset(reexport_apis)
    assert "pl" in reexport_apis


def test_polars_type_identity():
    """Test that re-exported objects are identical to originals."""
    import polars
    from cryoflow_plugin_collections.libs.polars import DataFrame, LazyFrame, col, pl

    # Verify objects are identical (not copies)
    assert pl is polars
    assert DataFrame is polars.DataFrame
    assert LazyFrame is polars.LazyFrame
    assert col is polars.col
