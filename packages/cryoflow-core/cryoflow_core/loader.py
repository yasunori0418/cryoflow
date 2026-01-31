"""Plugin loader for cryoflow."""

import importlib
import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Any

import pluggy

from cryoflow_core.config import CryoflowConfig, PluginConfig
from cryoflow_core.hookspecs import CryoflowSpecs, hookimpl
from cryoflow_core.plugin import BasePlugin, OutputPlugin, TransformPlugin


class PluginLoadError(Exception):
    """Raised when plugin loading fails."""


def _is_filesystem_path(module_str: str) -> bool:
    """Determine if a module string refers to a filesystem path."""
    return "/" in module_str or "\\" in module_str or module_str.endswith(".py") or module_str.startswith(".")


def _resolve_module_path(module_str: str, config_dir: Path) -> Path:
    """Resolve a module string to an absolute filesystem path.

    Absolute paths are normalized with resolve().
    Relative paths are resolved relative to config_dir.

    Raises:
        PluginLoadError: If the resolved path does not exist.
    """
    path = Path(module_str)
    if not path.is_absolute():
        path = config_dir / path
    resolved = path.resolve()
    if not resolved.exists():
        raise PluginLoadError(f"Plugin file does not exist: {resolved}")
    return resolved


def _load_module_from_path(name: str, path: Path) -> Any:
    """Load a Python module from a filesystem path.

    Raises:
        PluginLoadError: If the module cannot be loaded.
    """
    module_name = f"cryoflow_plugin_{name}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise PluginLoadError(f"Plugin '{name}': failed to create module spec from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        del sys.modules[module_name]
        raise PluginLoadError(f"Plugin '{name}': failed to execute module: {e}") from e
    return module


def _load_module_from_dotpath(name: str, module_path: str) -> Any:
    """Load a Python module from a dotted module path.

    Raises:
        PluginLoadError: If the module cannot be imported.
    """
    try:
        return importlib.import_module(module_path)
    except ImportError as e:
        raise PluginLoadError(f"Plugin '{name}': module '{module_path}' not found") from e


def _discover_plugin_classes(name: str, module: Any) -> list[type[BasePlugin]]:
    """Discover BasePlugin subclasses in a loaded module.

    Raises:
        PluginLoadError: If no subclasses are found.
    """
    classes: list[type[BasePlugin]] = []
    for obj in vars(module).values():
        if (
            inspect.isclass(obj)
            and issubclass(obj, BasePlugin)
            and obj not in (BasePlugin, TransformPlugin, OutputPlugin)
            and not inspect.isabstract(obj)
        ):
            classes.append(obj)
    if not classes:
        raise PluginLoadError(f"Plugin '{name}': no BasePlugin subclasses found in module")
    return classes


def _instantiate_plugins(name: str, classes: list[type[BasePlugin]], options: dict[str, Any]) -> list[BasePlugin]:
    """Instantiate discovered plugin classes with options.

    Raises:
        PluginLoadError: If instantiation fails.
    """
    instances: list[BasePlugin] = []
    for cls in classes:
        try:
            instances.append(cls(options))
        except Exception as e:
            raise PluginLoadError(f"Plugin '{name}': failed to instantiate {cls.__name__}: {e}") from e
    return instances


class _PluginHookRelay:
    """Wrapper that exposes plugin instances via pluggy hook methods."""

    def __init__(
        self,
        transforms: list[TransformPlugin],
        outputs: list[OutputPlugin],
    ) -> None:
        self._transforms = transforms
        self._outputs = outputs

    @hookimpl
    def register_transform_plugins(self) -> list[TransformPlugin]:
        return self._transforms

    @hookimpl
    def register_output_plugins(self) -> list[OutputPlugin]:
        return self._outputs


def _load_single_plugin(plugin_cfg: PluginConfig, config_dir: Path) -> list[BasePlugin]:
    """Load a single plugin from its config entry."""
    if _is_filesystem_path(plugin_cfg.module):
        path = _resolve_module_path(plugin_cfg.module, config_dir)
        module = _load_module_from_path(plugin_cfg.name, path)
    else:
        module = _load_module_from_dotpath(plugin_cfg.name, plugin_cfg.module)

    classes = _discover_plugin_classes(plugin_cfg.name, module)
    return _instantiate_plugins(plugin_cfg.name, classes, plugin_cfg.options)


def load_plugins(
    config: CryoflowConfig,
    config_path: Path,
    pm: pluggy.PluginManager | None = None,
) -> pluggy.PluginManager:
    """Load all enabled plugins and register them with pluggy.

    Args:
        config: The validated cryoflow configuration.
        config_path: Path to the config file (used to resolve relative plugin paths).
        pm: Optional existing PluginManager. Created if not provided.

    Returns:
        PluginManager with all plugins registered.

    Raises:
        PluginLoadError: If any enabled plugin fails to load.
    """
    if pm is None:
        pm = pluggy.PluginManager("cryoflow")
        pm.add_hookspecs(CryoflowSpecs)

    config_dir = config_path.parent.resolve()

    all_transforms: list[TransformPlugin] = []
    all_outputs: list[OutputPlugin] = []

    for plugin_cfg in config.plugins:
        if not plugin_cfg.enabled:
            continue

        instances = _load_single_plugin(plugin_cfg, config_dir)
        for inst in instances:
            if isinstance(inst, TransformPlugin):
                all_transforms.append(inst)
            elif isinstance(inst, OutputPlugin):
                all_outputs.append(inst)

    relay = _PluginHookRelay(all_transforms, all_outputs)
    pm.register(relay, name="cryoflow_plugin_relay")

    return pm


def get_transform_plugins(pm: pluggy.PluginManager) -> list[TransformPlugin]:
    """Retrieve registered TransformPlugin instances from the manager."""
    results: list[TransformPlugin] = []
    for plugin_list in pm.hook.register_transform_plugins():
        results.extend(plugin_list)
    return results


def get_output_plugins(pm: pluggy.PluginManager) -> list[OutputPlugin]:
    """Retrieve registered OutputPlugin instances from the manager."""
    results: list[OutputPlugin] = []
    for plugin_list in pm.hook.register_output_plugins():
        results.extend(plugin_list)
    return results
