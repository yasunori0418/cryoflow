# Contributing to cryoflow

Thank you for your interest in contributing to cryoflow.
This document covers everything you need to know to get started, from setting up your development environment to submitting a pull request.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Development Environment Setup](#development-environment-setup)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [Code Style](#code-style)
- [Commit Conventions](#commit-conventions)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Reporting Issues](#reporting-issues)

---

## Prerequisites

The following tools are required for development.

- [Nix](https://nixos.org/download/) (with Flakes enabled)
- [direnv](https://direnv.net/) (recommended) or Nix CLI

Without Nix, you need:

- Python 3.11 or later
- [uv](https://docs.astral.sh/uv/)

---

## Development Environment Setup

### Using direnv (Recommended)

```bash
# Clone the repository
git clone https://github.com/yasunori0418/cryoflow
cd cryoflow

# Copy the sample configuration
cp example.envrc .envrc

# Allow direnv to load the environment
direnv allow
```

When you enter the directory, direnv automatically activates the development environment defined in `dev/flake.nix`.
The following tools are included:

- `uv` - Python package management
- `ruff` - Formatter / linter
- `pyright` - Static type checker
- `actionlint` - GitHub Actions workflow linter

### Using Nix CLI

```bash
# Enter the development environment
nix develop ./dev
```

### Using uv (without Nix)

```bash
# Install dependencies
uv sync

# Activate the virtual environment
source .venv/bin/activate
```

---

## Project Structure

```
cryoflow/
├── cryoflow/                      # Meta-package (entry point)
├── packages/
│   ├── cryoflow-core/             # Core framework
│   │   ├── cryoflow_core/         # Source code
│   │   └── tests/                 # Test code
│   └── cryoflow-plugin-collections/  # Built-in plugin collection
│       ├── cryoflow_plugin_collections/
│       └── tests/
├── dev/
│   └── flake.nix                  # Development Nix Flake configuration
├── docs/                          # Documentation
│   ├── spec_ja.md / spec.md       # Specification
│   ├── plugin_development_ja.md / plugin_development.md
│   └── cicd_ja.md / cicd.md
├── examples/                      # Sample data and configurations
├── flake.nix                      # Nix Flake (root)
└── pyproject.toml                 # uv workspace configuration
```

The `packages/` directory is managed as a uv workspace, where each package has its own `pyproject.toml`.

---

## Running Tests

### Running in the Nix Development Environment (Recommended)

```bash
# Run all tests
pytest

# Run tests for a specific package
pytest packages/cryoflow-core/tests/
pytest packages/cryoflow-plugin-collections/tests/

# Verbose output
pytest -v
```

### Running in the Same Environment as CI

```bash
nix develop './dev#ci' -c pytest
```

Test paths are defined in `pyproject.toml` under `[tool.pytest.ini_options]`.

---

## Code Style

### Formatting / Linting (ruff)

```bash
# Check formatting
ruff format --check .

# Apply formatting
ruff format .

# Check linting
ruff check .

# Auto-fix linting issues
ruff check --fix .
```

Key settings (from `pyproject.toml`):

- Target version: Python 3.14
- Line length: 120 characters
- Quote style: single quotes

### Type Checking (pyright)

```bash
pyright
```

**Type annotations are required.**
All test code, documentation examples, and production code must include type annotations.
Avoid using `Any` unless absolutely necessary (e.g., required by a test scenario).

### Coding Conventions

- Use the `Result` type from the `returns` library for error handling
- Convert unexpected exceptions to `Failure` using the `@safe` decorator
- Follow the ABC base class interfaces for plugins
- All plugins must implement the `dry_run` method

---

## Commit Conventions

Commit messages must be written in **English**.

Follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <subject>

<body>  # optional

<footer>  # optional
```

### Types

| type | Usage |
| --- | --- |
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation changes only |
| `style` | Code style changes that do not affect functionality |
| `refactor` | Code changes that are neither bug fixes nor new features |
| `test` | Adding or modifying tests |
| `ci` | Changes to CI configuration |
| `chore` | Changes to build process or auxiliary tools |

### Examples

```
feat(plugin): add CSV input plugin

Add CsvInputPlugin that reads CSV files into LazyFrame.
Supports configurable delimiter and header options.
```

---

## Submitting a Pull Request

1. Fork the repository
2. Create a feature branch
   ```bash
   git checkout -b feat/your-feature-name
   ```
3. Make your changes and run the tests
4. Check your code style
5. Commit and push to your fork
6. Open a pull request targeting the `main` branch

When creating a pull request, follow the template in `.github/pull_request_template.md`.

### Pre-PR Checklist

- [ ] All tests pass locally
- [ ] Code style verified with `ruff format` and `ruff check`
- [ ] No type errors from `pyright`
- [ ] Tests added for new features
- [ ] Relevant documentation updated (both Japanese and English versions)

### Updating Documentation

Japanese documentation (`*_ja.md`) is the primary source. English documentation (`*.md`) should be updated to follow it.

---

## Reporting Issues

Please report bugs, feature requests, and questions via [GitHub Issues](https://github.com/yasunori0418/cryoflow/issues).

When reporting a bug, including the following information helps us respond quickly:

- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details (OS, Python version, cryoflow version)
- Relevant error messages or stack traces
