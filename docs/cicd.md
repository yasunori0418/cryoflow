# CI/CD Documentation

## Overview

The cryoflow project uses GitHub Actions to configure its CI/CD pipeline.
Dependency updates are automatically managed by Renovate Bot.

All workflows use Nix to standardize the build environment, installing Nix and configuring Cachix through a shared composite action (`setup-nix`).

---

## Architecture Overview

```
[Push to feature branch / Pull Request]
        |
        v
    [Test] ← Runs when packages/**/*.py or uv.lock changes

[Push to main branch]
        |
        v
    [Release] ← Runs automatically when packages/** changes
        |
        v (auto-triggered after Release succeeds)
    [Publish to PyPI]

[Tag push (*.*.*)]
        |
        v
    [Cachix Push] ← Builds and pushes multi-platform Nix packages

[Manual execution only]
    [Bump Version] ← Updates version across all packages, commits and pushes
```

---

## Workflow Details

### 1. Test (`test.yml`)

| Item | Content |
|------|---------|
| Trigger | Push to non-main branches, PR, manual execution |
| Target paths | `packages/**/*.py`, `uv.lock` |
| Runner | `ubuntu-latest` |

#### Overview

Runs tests when Python source files or lock files change on pushes to non-main branches or pull requests.

#### Steps

1. Checkout repository
2. Setup Nix environment (`setup-nix` composite action)
3. Run pytest in the CI-dedicated Nix dev environment (`dev#ci`)

#### Environment Variables

| Variable | Value | Purpose |
|----------|-------|---------|
| `TERM` | `"dumb"` | Avoids terminal emulation issues when running pytest |

---

### 2. Release (`release.yml`)

| Item | Content |
|------|---------|
| Trigger | Push to `main` branch, manual execution |
| Target paths | `packages/**` |
| Runner | `ubuntu-latest` |
| Required permissions | `contents: write` |

#### Overview

Automatically creates a GitHub Release when changes under `packages/` are merged to the `main` branch, using the current version as the release tag.

#### Steps

1. Checkout repository (full history: `fetch-depth: 0`)
2. Setup Nix environment
3. Get project version via `uv version`
4. Create GitHub Release with `softprops/action-gh-release` (release notes auto-generated)

#### Version Resolution

```bash
VERSION=$(nix shell 'nixpkgs#uv' -c uv version | awk '{print $2}')
```

The version from the root `pyproject.toml` is used as both the tag name and release name.

---

### 3. Publish to PyPI (`publish.yml`)

| Item | Content |
|------|---------|
| Trigger | After Release workflow completes, manual execution |
| Runner | `ubuntu-latest` |
| Required permissions | `contents: read` |

#### Overview

Automatically triggered after the Release workflow succeeds, publishing all packages to PyPI.
When run manually, a specific version can be published by specifying a tag name.

#### Trigger Conditions

- Via `workflow_run`: Runs only when the Release workflow completes with `success`
- Via `workflow_dispatch`: `tag_name` input parameter is required

#### Steps

1. Checkout repository
   - Via `workflow_run`: Uses the HEAD commit of the Release workflow
   - Via `workflow_dispatch`: Uses the current SHA
2. Setup Nix environment
3. Build all packages: `uv build --all-packages`
4. Publish to PyPI: `uv publish`

#### Required Secrets

| Secret name | Purpose |
|------------|---------|
| `PYPI_TOKEN` | Authentication token for PyPI |

---

### 4. Bump Version (`bump-version.yml`)

| Item | Content |
|------|---------|
| Trigger | Manual execution only (`workflow_dispatch`) |
| Executable branches | Non-main branches only |
| Runner | `ubuntu-latest` |
| Required permissions | `contents: write` |

#### Overview

Updates the version across all packages at once, then commits and pushes the changes.
Intended to be run on a `feature` or `release` branch before merging to main.

#### Input Parameters

| Parameter | Description | Required | Example |
|-----------|-------------|----------|---------|
| `version` | New version number | Required | `1.0.0` |

#### Steps

1. Checkout repository
2. Setup Nix environment
3. Update version for all packages:
   - Root package (`cryoflow`)
   - `cryoflow-core`
   - `cryoflow-plugin-collections`
4. Commit and push changes
   - Committer: `github-actions[bot]`
   - Commit message: `chore: bump version to {version}`

#### Modified Files

- `pyproject.toml` (root)
- `packages/cryoflow-core/pyproject.toml`
- `packages/cryoflow-plugin-collections/pyproject.toml`

---

### 5. Cachix Push (`cachix-push.yml`)

| Item | Content |
|------|---------|
| Trigger | Version tag push (`*.*.*`), manual execution |
| Runner | Matrix (multiple platforms) |

#### Overview

When a version tag is pushed, builds Nix packages for multiple platforms and pushes them to Cachix.

#### Build Matrix

| OS | System |
|----|--------|
| `ubuntu-latest` | `x86_64-linux` |
| `ubuntu-24.04-arm` | `aarch64-linux` |
| `macos-latest` | `aarch64-darwin` |

#### Steps

For each platform:

1. Checkout repository
2. Setup Nix environment (with Cachix write access)
3. Build Nix packages:
   - `nix build .#default` - Production package
   - `nix build .#test` - Test environment package

Built artifacts are automatically pushed to the `yasunori0418` Cachix cache.

---

## Shared Infrastructure

### Setup Nix Action (`.github/actions/setup-nix`)

A composite action used by all workflows.

#### Steps

1. Install Nix with `cachix/install-nix-action`
2. Configure the `yasunori0418` Cachix cache with `cachix/cachix-action`

#### Input Parameters

| Parameter | Description | Required |
|-----------|-------------|----------|
| `cachix-auth-token` | Cachix authentication token | Optional |

#### Required Secrets

| Secret name | Purpose |
|------------|---------|
| `CACHIX_AUTH_TOKEN` | Authentication/write token for Cachix |

---

## Dependency Auto-Updates (Renovate)

Renovate Bot automatically updates the following dependencies.

### Managed Dependencies

| Manager | Target |
|---------|--------|
| `pep621` | Python libraries (`pyproject.toml`) |
| `nix` | Nix flake inputs (`flake.nix`, `dev/flake.nix`) |
| `github-actions` | GitHub Actions versions |

### Update Rules

| Rule | Content |
|------|---------|
| Python libraries | Individual PR per library |
| Root `flake.nix` inputs | Grouped as `nix flake inputs (root)` |
| `dev/flake.nix` inputs | Grouped as `nix flake inputs (dev)` |
| Lock file maintenance | Runs every Monday before 5am |

---

## Release Flow

The typical release process is as follows:

```
1. Develop and test on a feature branch (Test workflow)
2. Run Bump Version workflow (manual) to update the version
3. Merge PR to main branch
4. Release workflow runs automatically → GitHub Release created
5. Publish workflow runs automatically → Published to PyPI
6. Cachix Push workflow reacts to tag → Nix packages built and cached
```
