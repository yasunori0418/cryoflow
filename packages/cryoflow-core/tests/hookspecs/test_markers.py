"""Tests for hookspec marker project names."""

from cryoflow_core.hookspecs import hookimpl, hookspec


class TestMarkers:
    def test_hookspec_project_name(self):
        assert hookspec.project_name == 'cryoflow'

    def test_hookimpl_project_name(self):
        assert hookimpl.project_name == 'cryoflow'
