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
