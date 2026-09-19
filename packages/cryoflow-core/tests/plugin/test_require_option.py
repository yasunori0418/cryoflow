"""Tests for BasePlugin.require_option."""

from pathlib import Path

from returns.result import Failure, Success

from ..conftest import DummyTransformPlugin


class TestRequireOption:
    """Tests for BasePlugin.require_option."""

    def test_returns_success_when_option_exists(self, tmp_path: Path) -> None:
        """Test that an existing option is returned as Success."""
        plugin = DummyTransformPlugin({'threshold': 10}, tmp_path)

        result = plugin.require_option('threshold')

        assert isinstance(result, Success)
        assert result.unwrap() == 10

    def test_returns_failure_when_option_missing(self, tmp_path: Path) -> None:
        """Test that a missing option is returned as Failure."""
        plugin = DummyTransformPlugin({}, tmp_path)

        result = plugin.require_option('threshold')

        assert isinstance(result, Failure)
        error = result.failure()
        assert isinstance(error, ValueError)
        assert str(error) == "Option 'threshold' is required"

    def test_returns_failure_when_option_is_none(self, tmp_path: Path) -> None:
        """Test that an option explicitly set to None is treated as missing."""
        plugin = DummyTransformPlugin({'threshold': None}, tmp_path)

        result = plugin.require_option('threshold')

        assert isinstance(result, Failure)
        error = result.failure()
        assert isinstance(error, ValueError)
        assert str(error) == "Option 'threshold' is required"
