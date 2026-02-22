"""Tests for returns re-export in libs subpackage."""


def test_returns_reexport() -> None:
    """Test returns re-export works correctly."""
    from cryoflow_plugin_collections.libs.returns.result import Failure, Result, Success

    # Verify Success works
    result: Result[int, str] = Success(42)
    assert result.unwrap() == 42

    # Verify Failure works
    error_result: Result[int, str] = Failure('error')
    assert isinstance(error_result, Failure)


def test_returns_individual_imports() -> None:
    """Test importing individual types/functions from returns re-export."""
    from cryoflow_plugin_collections.libs.returns.result import (
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

    error_result: Result[int, str] = Failure('error')
    assert isinstance(error_result, Failure)

    # Test safe decorator
    @safe
    def may_fail(x: int) -> int:
        if x < 0:
            raise ValueError('negative')
        return x * 2

    success_result = may_fail(5)
    assert success_result.unwrap() == 10

    failure_result = may_fail(-1)
    assert isinstance(failure_result, Failure)


def test_returns_extended_apis() -> None:
    """Test maybe APIs are available."""
    from cryoflow_plugin_collections.libs.returns.maybe import (
        Maybe,
        Nothing,
        Some,
    )

    # Test Maybe monad
    some_value: Maybe[int] = Some(42)
    assert some_value.unwrap() == 42

    # Nothing is a singleton value, not a container instance
    assert Nothing is not None


def test_returns_complete_api_export() -> None:
    """Test that result and maybe submodule APIs are exported."""
    from cryoflow_plugin_collections.libs.returns import maybe as maybe_module
    from cryoflow_plugin_collections.libs.returns import result as result_module

    # Verify result types are present
    assert 'Result' in result_module.__all__
    assert 'Success' in result_module.__all__
    assert 'Failure' in result_module.__all__
    assert 'ResultE' in result_module.__all__
    assert 'safe' in result_module.__all__

    # Verify maybe types are present
    assert 'Maybe' in maybe_module.__all__
    assert 'Some' in maybe_module.__all__
    assert 'Nothing' in maybe_module.__all__
    assert 'maybe' in maybe_module.__all__


def test_returns_type_identity() -> None:
    """Test that re-exported objects are identical to originals."""
    import returns.maybe
    import returns.result

    from cryoflow_plugin_collections.libs.returns.maybe import (
        Maybe,
        Nothing,
        Some,
    )
    from cryoflow_plugin_collections.libs.returns.result import (
        Failure,
        Result,
        Success,
        safe,
    )

    # Verify result objects are identical (not copies)
    assert Result is returns.result.Result
    assert Success is returns.result.Success
    assert Failure is returns.result.Failure
    assert safe is returns.result.safe

    # Verify maybe objects are identical (not copies)
    assert Maybe is returns.maybe.Maybe
    assert Nothing is returns.maybe.Nothing
    assert Some is returns.maybe.Some
