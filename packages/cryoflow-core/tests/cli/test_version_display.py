"""Tests for CLI version display."""

from typer.testing import CliRunner

from cryoflow_core.cli import app

runner = CliRunner()


class TestVersionDisplay:
    def test_version_flag(self) -> None:
        result = runner.invoke(app, ['--version'])
        assert result.exit_code == 0
        assert 'cryoflow version' in result.output
        assert 'cryoflow-plugin-collections version' in result.output

    def test_version_short_flag(self) -> None:
        result = runner.invoke(app, ['-v'])
        assert result.exit_code == 0
        assert 'cryoflow version' in result.output
        assert 'cryoflow-plugin-collections version' in result.output
