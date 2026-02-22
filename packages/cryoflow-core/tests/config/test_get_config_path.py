"""Tests for get_config_path function."""

from pathlib import Path
from unittest.mock import patch

from cryoflow_core.config import get_config_path


class TestGetConfigPath:
    def test_returns_xdg_path(self):
        fake_home = Path('/tmp/fakexdg')
        with patch('cryoflow_core.config.xdg_config_home', return_value=fake_home):
            result = get_config_path(None)
        assert result == fake_home / 'cryoflow' / 'config.toml'

    def test_returns_target_config_path(self):
        fake_home = Path('/tmp/fakexdg')
        target_config_path = Path('/tmp/target/config.toml')
        with patch('cryoflow_core.config.xdg_config_home', return_value=fake_home):
            result = get_config_path(target_config_path)
        assert result == target_config_path
