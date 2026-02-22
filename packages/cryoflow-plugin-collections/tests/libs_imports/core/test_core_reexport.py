"""Tests for cryoflow-core re-export in libs subpackage."""


def test_core_reexport() -> None:
    """Test core re-export works correctly."""
    from cryoflow_plugin_collections.libs.core import (
        FrameData,
        InputPlugin,
        OutputPlugin,
        TransformPlugin,
    )

    # Verify imports are accessible
    assert FrameData is not None
    assert TransformPlugin is not None
    assert InputPlugin is not None
    assert OutputPlugin is not None


def test_backward_compatibility_direct_imports() -> None:
    """Verify existing direct import pattern still works."""
    import polars as pl
    from returns.result import Success

    from cryoflow_core.plugin import TransformPlugin

    # All should be accessible
    assert pl is not None
    assert Success is not None
    assert TransformPlugin is not None
