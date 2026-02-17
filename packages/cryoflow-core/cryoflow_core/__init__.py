"""cryoflow-core: Core framework for cryoflow CLI tool."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version('cryoflow-core')
except PackageNotFoundError:
    # Fallback for development environment
    __version__ = 'unknown'
