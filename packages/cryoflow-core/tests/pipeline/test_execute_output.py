"""Tests for execute_output function."""

from pathlib import Path
from typing import Any

import polars as pl
from returns.result import Failure, Success

from cryoflow_core.pipeline import execute_output
from cryoflow_core.plugin import FrameData, OutputPlugin


class TestExecuteOutput:
    """Tests for output plugin execution."""

    def test_output_success_data(self, sample_lazyframe, tmp_path: Path) -> None:
        """Test output with successful data."""
        from returns.result import Success as SuccessResult

        class DummyOutputPlugin(OutputPlugin):
            def name(self) -> str:
                return 'dummy_output'

            def execute(self, df: FrameData) -> SuccessResult[None]:
                return SuccessResult(None)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        plugin = DummyOutputPlugin({}, tmp_path)
        data = Success(sample_lazyframe)
        result = execute_output(data, [plugin])
        assert isinstance(result, Success)

    def test_output_failure_data(self, tmp_path: Path) -> None:
        """Test output with failed data (should not execute plugin)."""
        from returns.result import Success as SuccessResult

        class DummyOutputPlugin(OutputPlugin):
            def name(self) -> str:
                return 'dummy_output'

            def execute(self, df: FrameData) -> SuccessResult[None]:
                return SuccessResult(None)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        plugin = DummyOutputPlugin({}, tmp_path)
        error = ValueError('data processing error')
        data = Failure(error)
        result = execute_output(data, [plugin])
        assert isinstance(result, Failure)
        assert result.failure() == error

    def test_output_empty_plugins(self, sample_lazyframe) -> None:
        """Test output with empty plugin list returns Success(None)."""
        data = Success(sample_lazyframe)
        result = execute_output(data, [])
        assert isinstance(result, Success)

    def test_multiple_output_plugins_all_succeed(self, sample_lazyframe, tmp_path: Path) -> None:
        """Test that all output plugins are executed when data succeeds."""
        from returns.result import Success as SuccessResult

        executed = []

        class TrackingOutputPlugin(OutputPlugin):
            def __init__(self, track_id: str, options: dict[str, Any], config_dir: Path) -> None:
                super().__init__(options, config_dir)
                self._track_id = track_id

            def name(self) -> str:
                return f'tracking_{self._track_id}'

            def execute(self, df: FrameData) -> SuccessResult[None]:
                executed.append(self._track_id)
                return SuccessResult(None)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        plugins: list[OutputPlugin] = [
            TrackingOutputPlugin('first', {}, tmp_path),
            TrackingOutputPlugin('second', {}, tmp_path),
        ]
        data = Success(sample_lazyframe)
        result = execute_output(data, plugins)
        assert isinstance(result, Success)
        assert executed == ['first', 'second']

    def test_multiple_output_plugins_stops_on_failure(self, sample_lazyframe, tmp_path: Path) -> None:
        """Test that execution stops when a plugin fails."""
        from returns.result import Failure as FailureResult, Success as SuccessResult

        executed = []

        class FailingOutputPlugin(OutputPlugin):
            def name(self) -> str:
                return 'failing_output'

            def execute(self, df: FrameData) -> FailureResult[Exception]:
                executed.append('failing')
                return FailureResult(ValueError('output failed'))

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        class AfterOutputPlugin(OutputPlugin):
            def name(self) -> str:
                return 'after_output'

            def execute(self, df: FrameData) -> SuccessResult[None]:
                executed.append('after')
                return SuccessResult(None)

            def dry_run(self, schema: dict[str, pl.DataType]) -> SuccessResult[dict[str, pl.DataType]]:
                return SuccessResult(schema)

        plugins = [
            FailingOutputPlugin({}, tmp_path),
            AfterOutputPlugin({}, tmp_path),
        ]
        data = Success(sample_lazyframe)
        result = execute_output(data, plugins)
        assert isinstance(result, Failure)
        assert executed == ['failing']
