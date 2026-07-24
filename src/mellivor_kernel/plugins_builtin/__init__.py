"""Built-in kernel plugins -- demonstrations of the Plugin Runtime
Foundation (`mellivor_kernel.plugins`, ADR-0014) and Plugin SDK
(`mellivor_kernel.plugin_sdk`, ADR-0015), not part of either package's
own contract.

Exactly one built-in plugin exists at this sprint's scope --
`SystemInfoPlugin` -- see ADR-0016. Like `tools.builtin`, this package is
exported separately from the layers it demonstrates and is not itself a
new kernel responsibility under ADR-0002.
"""

from __future__ import annotations

from mellivor_kernel.plugins_builtin.system_info import SystemInfoPlugin, SystemInfoSnapshot

__all__ = [
    "SystemInfoPlugin",
    "SystemInfoSnapshot",
]
