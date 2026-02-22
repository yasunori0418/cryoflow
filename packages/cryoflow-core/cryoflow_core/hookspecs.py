"""Pluggy hook specifications for cryoflow."""

import pluggy

from cryoflow_core.plugin import InputPlugin, OutputPlugin, TransformPlugin

hookspec = pluggy.HookspecMarker('cryoflow')
hookimpl = pluggy.HookimplMarker('cryoflow')


class CryoflowSpecs:
    """Hook specifications for cryoflow plugin system."""

    @hookspec
    def register_input_plugins(self) -> list[InputPlugin]:  # pyright: ignore[reportReturnType]
        """Return a list of input plugin instances."""

    @hookspec
    def register_transform_plugins(self) -> list[TransformPlugin]:  # pyright: ignore[reportReturnType]
        """Return a list of transform plugin instances."""

    @hookspec
    def register_output_plugins(self) -> list[OutputPlugin]:  # pyright: ignore[reportReturnType]
        """Return a list of output plugin instances."""
