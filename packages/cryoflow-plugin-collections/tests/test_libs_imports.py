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
