"""Tests for _is_filesystem_path function."""

import pytest

from cryoflow_core.loader import _is_filesystem_path


class TestIsFilesystemPath:
    @pytest.mark.parametrize(
        'input_str,expected',
        [
            ('./plugins/my_plugin.py', True),
            ('../plugins/my_plugin.py', True),
            ('/absolute/path/to/plugin.py', True),
            ('relative/path/to/plugin.py', True),
            ('plugin.py', True),
            ('C:\\Windows\\path.py', True),
            ('.', True),
            ('my_package.submodule', False),
            ('cryoflow_core.plugin', False),
            ('simple_module', False),
        ],
    )
    def test_patterns(self, input_str, expected):
        assert _is_filesystem_path(input_str) == expected
