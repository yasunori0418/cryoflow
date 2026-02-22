"""Tests for IpcScanPlugin."""

from pathlib import Path
from tempfile import TemporaryDirectory

import polars as pl
from returns.result import Failure, Success

from cryoflow_plugin_collections.input.ipc_scan import IpcScanPlugin


class TestIpcScanPlugin:
    """Tests for IpcScanPlugin."""

    def test_execute_returns_lazyframe(self, tmp_path: Path) -> None:
        """Test that execute returns a LazyFrame."""
        ipc_path = tmp_path / 'input.arrow'
        df = pl.DataFrame({'value': [1, 2, 3], 'name': ['a', 'b', 'c']})
        df.write_ipc(ipc_path)
        plugin = IpcScanPlugin({'input_path': str(ipc_path)}, tmp_path)

        result = plugin.execute()

        assert isinstance(result, Success)
        assert isinstance(result.unwrap(), pl.LazyFrame)

    def test_execute_data_correctness(self, tmp_path: Path) -> None:
        """Test that execute returns correct data."""
        ipc_path = tmp_path / 'input.arrow'
        df = pl.DataFrame({'value': [10, 20, 30], 'name': ['a', 'b', 'c']})
        df.write_ipc(ipc_path)
        plugin = IpcScanPlugin({'input_path': str(ipc_path)}, tmp_path)

        result = plugin.execute()

        assert isinstance(result, Success)
        lazy_result = result.unwrap()
        assert isinstance(lazy_result, pl.LazyFrame)
        collected = lazy_result.collect()
        assert collected.to_dict(as_series=False) == {
            'value': [10, 20, 30],
            'name': ['a', 'b', 'c'],
        }

    def test_execute_missing_input_path(self, tmp_path: Path) -> None:
        """Test error when input_path option is missing."""
        plugin = IpcScanPlugin({}, tmp_path)

        result = plugin.execute()

        assert isinstance(result, Failure)
        assert isinstance(result.failure(), ValueError)
        assert 'input_path' in str(result.failure())

    def test_execute_file_not_found(self, tmp_path: Path) -> None:
        """Test error when input file does not exist."""
        plugin = IpcScanPlugin(
            {'input_path': str(tmp_path / 'nonexistent.arrow')}, tmp_path
        )

        result = plugin.execute()

        assert isinstance(result, Failure)
        assert isinstance(result.failure(), FileNotFoundError)

    def test_execute_with_relative_path(self) -> None:
        """Test that relative paths are resolved relative to config_dir."""
        with TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / 'config'
            config_dir.mkdir()
            data_dir = config_dir / 'data'
            data_dir.mkdir()
            ipc_path = data_dir / 'input.arrow'
            pl.DataFrame({'value': [1, 2, 3]}).write_ipc(ipc_path)
            plugin = IpcScanPlugin({'input_path': 'data/input.arrow'}, config_dir)

            result = plugin.execute()

            assert isinstance(result, Success)
            assert isinstance(result.unwrap(), pl.LazyFrame)

    def test_dry_run_returns_schema(self, tmp_path: Path) -> None:
        """Test successful dry_run returns schema dict."""
        ipc_path = tmp_path / 'input.arrow'
        df = pl.DataFrame({'value': [1, 2, 3], 'name': ['a', 'b', 'c']})
        df.write_ipc(ipc_path)
        plugin = IpcScanPlugin({'input_path': str(ipc_path)}, tmp_path)

        result = plugin.dry_run()

        assert isinstance(result, Success)
        schema = result.unwrap()
        assert isinstance(schema, dict)
        assert schema['value'] == pl.Int64()
        assert schema['name'] == pl.String()

    def test_dry_run_missing_input_path(self, tmp_path: Path) -> None:
        """Test dry_run error when input_path option is missing."""
        plugin = IpcScanPlugin({}, tmp_path)

        result = plugin.dry_run()

        assert isinstance(result, Failure)
        assert isinstance(result.failure(), ValueError)
        assert 'input_path' in str(result.failure())

    def test_dry_run_file_not_found(self, tmp_path: Path) -> None:
        """Test dry_run error when input file does not exist."""
        plugin = IpcScanPlugin(
            {'input_path': str(tmp_path / 'nonexistent.arrow')}, tmp_path
        )

        result = plugin.dry_run()

        assert isinstance(result, Failure)
        assert isinstance(result.failure(), FileNotFoundError)

    def test_dry_run_with_relative_path(self) -> None:
        """Test dry_run with relative paths resolved relative to config_dir."""
        with TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / 'config'
            config_dir.mkdir()
            data_dir = config_dir / 'data'
            data_dir.mkdir()
            ipc_path = data_dir / 'input.arrow'
            pl.DataFrame({'value': [1, 2, 3]}).write_ipc(ipc_path)
            plugin = IpcScanPlugin({'input_path': 'data/input.arrow'}, config_dir)

            result = plugin.dry_run()

            assert isinstance(result, Success)
            assert isinstance(result.unwrap(), dict)

    def test_name(self, tmp_path: Path) -> None:
        """Test plugin name."""
        plugin = IpcScanPlugin({}, tmp_path)

        assert plugin.name() == 'ipc_scan'
