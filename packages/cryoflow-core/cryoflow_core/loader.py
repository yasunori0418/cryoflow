"""Plugin loader for cryoflow."""

import importlib
import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Any, TypeVar

import pluggy
from returns.result import Failure, Result, Success

from cryoflow_core.config import CryoflowConfig, PluginConfig
from cryoflow_core.hookspecs import CryoflowSpecs, hookimpl
from cryoflow_core.plugin import BasePlugin, InputPlugin, OutputPlugin, TransformPlugin


class PluginLoadError(Exception):
    """Raised when plugin loading fails."""


def _is_filesystem_path(module_str: str) -> bool:
    """Determine if a module string refers to a filesystem path."""
    return '/' in module_str or '\\' in module_str or module_str.endswith('.py') or module_str.startswith('.')


def _resolve_module_path(module_str: str, config_dir: Path) -> Result[Path, PluginLoadError]:
    """Resolve a module string to an absolute filesystem path.

    Absolute paths are normalized with resolve().
    Relative paths are resolved relative to config_dir.

    Returns:
        Success containing the resolved path.
        Failure containing PluginLoadError if the resolved path does not exist.
    """
    path = Path(module_str)
    if not path.is_absolute():
        path = config_dir / path
    resolved = path.resolve()
    if not resolved.exists():
        return Failure(PluginLoadError(f'Plugin file does not exist: {resolved}'))
    return Success(resolved)


def _load_module_from_path(name: str, path: Path) -> Result[Any, PluginLoadError]:
    """Load a Python module from a filesystem path.

    Returns:
        Success containing the loaded module.
        Failure containing PluginLoadError if the module cannot be loaded.
    """
    module_name = f'cryoflow_plugin_{name}'
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        return Failure(PluginLoadError(f"Plugin '{name}': failed to create module spec from {path}"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        del sys.modules[module_name]
        return Failure(PluginLoadError(f"Plugin '{name}': failed to execute module: {e}"))
    return Success(module)


def _load_module_from_dotpath(name: str, module_path: str) -> Result[Any, PluginLoadError]:
    """Load a Python module from a dotted module path.

    Returns:
        Success containing the imported module.
        Failure containing PluginLoadError if the module cannot be imported.
    """
    try:
        return Success(importlib.import_module(module_path))
    except ImportError as e:
        error = PluginLoadError(f"Plugin '{name}': module '{module_path}' not found")
        error.__cause__ = e
        return Failure(error)


def _discover_plugin_classes(name: str, module: Any) -> Result[list[type[BasePlugin]], PluginLoadError]:
    """Discover BasePlugin subclasses in a loaded module.

    Returns:
        Success containing the discovered plugin classes.
        Failure containing PluginLoadError if no subclasses are found.
    """
    classes: list[type[BasePlugin]] = []
    for obj in vars(module).values():
        if (
            inspect.isclass(obj)
            and issubclass(obj, BasePlugin)
            and obj not in (BasePlugin, InputPlugin, TransformPlugin, OutputPlugin)
            and not inspect.isabstract(obj)
        ):
            classes.append(obj)
    if not classes:
        return Failure(PluginLoadError(f"Plugin '{name}': no BasePlugin subclasses found in module"))
    return Success(classes)


def _instantiate_plugins(
    name: str,
    classes: list[type[BasePlugin]],
    options: dict[str, Any],
    config_dir: Path,
    label: str = 'default',
) -> Result[list[BasePlugin], PluginLoadError]:
    """Instantiate discovered plugin classes with options.

    Args:
        name: Plugin name for error messages.
        classes: List of plugin classes to instantiate.
        options: Plugin options dictionary.
        config_dir: Directory containing the config file (for path resolution).
        label: Data stream identifier to pass to plugin instances.

    Returns:
        Success containing the instantiated plugins.
        Failure containing PluginLoadError if instantiation fails.
    """
    instances: list[BasePlugin] = []
    for cls in classes:
        try:
            instances.append(cls(options, config_dir, label))
        except Exception as e:
            return Failure(PluginLoadError(f"Plugin '{name}': failed to instantiate {cls.__name__}: {e}"))
    return Success(instances)


class _PluginHookRelay:
    """Wrapper that exposes plugin instances via pluggy hook methods."""

    def __init__(
        self,
        inputs: list[InputPlugin],
        transforms: list[TransformPlugin],
        outputs: list[OutputPlugin],
    ) -> None:
        self._inputs = inputs
        self._transforms = transforms
        self._outputs = outputs

    @hookimpl
    def register_input_plugins(self) -> list[InputPlugin]:
        return self._inputs

    @hookimpl
    def register_transform_plugins(self) -> list[TransformPlugin]:
        return self._transforms

    @hookimpl
    def register_output_plugins(self) -> list[OutputPlugin]:
        return self._outputs


def _load_single_plugin(plugin_cfg: PluginConfig, config_dir: Path) -> Result[list[BasePlugin], PluginLoadError]:
    """Load a single plugin from its config entry.

    Args:
        plugin_cfg: Plugin configuration.
        config_dir: Directory containing the config file (for path resolution).

    Returns:
        Success containing the instantiated plugin instances.
        Failure containing PluginLoadError if plugin loading fails.
    """
    if _is_filesystem_path(plugin_cfg.module):
        module_result = _resolve_module_path(plugin_cfg.module, config_dir).bind(
            lambda path: _load_module_from_path(plugin_cfg.name, path)
        )
    else:
        module_result = _load_module_from_dotpath(plugin_cfg.name, plugin_cfg.module)

    return module_result.bind(lambda module: _discover_plugin_classes(plugin_cfg.name, module)).bind(
        lambda classes: _instantiate_plugins(plugin_cfg.name, classes, plugin_cfg.options, config_dir, plugin_cfg.label)
    )


def load_plugins(
    config: CryoflowConfig,
    config_path: Path,
    pm: pluggy.PluginManager | None = None,
) -> Result[pluggy.PluginManager, PluginLoadError]:
    """Load all enabled plugins and register them with pluggy.

    Args:
        config: The validated cryoflow configuration.
        config_path: Path to the config file (used to resolve relative plugin paths).
        pm: Optional existing PluginManager. Created if not provided.

    Returns:
        Success containing the PluginManager with all plugins registered.
        Failure containing PluginLoadError if any enabled plugin fails to load.
    """
    if pm is None:
        pm = pluggy.PluginManager('cryoflow')
        pm.add_hookspecs(CryoflowSpecs)

    config_dir = config_path.parent.resolve()

    all_inputs: list[InputPlugin] = []
    all_transforms: list[TransformPlugin] = []
    all_outputs: list[OutputPlugin] = []

    for plugin_cfg in config.input_plugins:
        if not plugin_cfg.enabled:
            continue

        result = _load_single_plugin(plugin_cfg, config_dir)
        if isinstance(result, Failure):
            return Failure(result.failure())
        for inst in result.unwrap():
            if isinstance(inst, InputPlugin):
                all_inputs.append(inst)

    for plugin_cfg in config.transform_plugins:
        if not plugin_cfg.enabled:
            continue

        result = _load_single_plugin(plugin_cfg, config_dir)
        if isinstance(result, Failure):
            return Failure(result.failure())
        for inst in result.unwrap():
            if isinstance(inst, TransformPlugin):
                all_transforms.append(inst)

    for plugin_cfg in config.output_plugins:
        if not plugin_cfg.enabled:
            continue

        result = _load_single_plugin(plugin_cfg, config_dir)
        if isinstance(result, Failure):
            return Failure(result.failure())
        for inst in result.unwrap():
            if isinstance(inst, OutputPlugin):
                all_outputs.append(inst)

    relay = _PluginHookRelay(all_inputs, all_transforms, all_outputs)
    pm.register(relay, name='cryoflow_plugin_relay')

    return Success(pm)


T = TypeVar('T', bound=BasePlugin)

# Plugin type to hook name mapping
_PLUGIN_TYPE_HOOKS: dict[type[BasePlugin], str] = {
    InputPlugin: 'register_input_plugins',
    TransformPlugin: 'register_transform_plugins',
    OutputPlugin: 'register_output_plugins',
}


def get_plugins(pm: pluggy.PluginManager, plugin_type: type[T]) -> list[T]:
    """Retrieve registered plugin instances of the specified type.

    Args:
        pm: The PluginManager instance.
        plugin_type: The plugin class type (must be a subclass of BasePlugin).

    Returns:
        List of plugin instances of the specified type.

    Raises:
        ValueError: If the plugin_type is not supported (not in _PLUGIN_TYPE_HOOKS).

    Examples:
        >>> inputs = get_plugins(pm, InputPlugin)
        >>> transforms = get_plugins(pm, TransformPlugin)
        >>> outputs = get_plugins(pm, OutputPlugin)
    """
    hook_name = _PLUGIN_TYPE_HOOKS.get(plugin_type)
    if hook_name is None:
        raise ValueError(f'Unsupported plugin type: {plugin_type}')

    hook_caller = getattr(pm.hook, hook_name)
    results: list[T] = []
    for plugin_list in hook_caller():
        results.extend(plugin_list)
    return results
