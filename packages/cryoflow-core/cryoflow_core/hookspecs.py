"""Pluggy hook specifications for cryoflow."""

import pluggy

from cryoflow_core.plugin import OutputPlugin, TransformPlugin

hookspec = pluggy.HookspecMarker("cryoflow")
hookimpl = pluggy.HookimplMarker("cryoflow")


class CryoflowSpecs:
    """Hook specifications for cryoflow plugin system."""

    @hookspec
    def register_transform_plugins(self) -> list[TransformPlugin]:
        """Return a list of transform plugin instances."""

    @hookspec
    def register_output_plugins(self) -> list[OutputPlugin]:
        """Return a list of output plugin instances."""
