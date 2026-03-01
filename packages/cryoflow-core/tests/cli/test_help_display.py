"""Tests for CLI help display."""

from typer.testing import CliRunner

from cryoflow_core.cli import app

runner = CliRunner(env={"NO_COLOR": "1"})


class TestHelpDisplay:
    def test_no_args_shows_help(self) -> None:
        result = runner.invoke(app, [])
        # Typer with no_args_is_help may return 0 or 2 depending on version
        assert result.exit_code in (0, 2)
        assert 'Usage' in result.output or 'usage' in result.output.lower()

    def test_help_flag(self) -> None:
        result = runner.invoke(app, ['--help'])
        assert result.exit_code == 0
        assert 'Usage' in result.output

    def test_help_short_flag(self) -> None:
        result = runner.invoke(app, ['-h'])
        assert result.exit_code == 0
        assert 'Usage' in result.output

    def test_run_help(self) -> None:
        result = runner.invoke(app, ['run', '--help'])
        assert result.exit_code == 0
        assert '--config' in result.output

    def test_run_help_short_flag(self) -> None:
        result = runner.invoke(app, ['run', '-h'])
        assert result.exit_code == 0
        assert '--config' in result.output

    def test_check_help_short_flag(self) -> None:
        result = runner.invoke(app, ['check', '-h'])
        assert result.exit_code == 0
        assert '--config' in result.output
