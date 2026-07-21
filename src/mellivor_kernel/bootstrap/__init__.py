"""Public API of the kernel's bootstrap and composition layer.

This package assembles the existing subsystems (``core``, ``config``,
``providers``, ``tools``) into a running kernel. It intentionally sits
above all of them, rather than inside any one of them: composing multiple
subsystems together is not something any single subsystem can own without
depending on its siblings, which would break the acyclic dependency graph
those subsystems otherwise maintain (``core`` depends on none of them;
``config``/``providers``/``tools`` each depend only on ``core``).
"""

from __future__ import annotations

from mellivor_kernel.bootstrap.bootstrap import KernelBootstrap
from mellivor_kernel.bootstrap.builder import BootstrapBuilder
from mellivor_kernel.bootstrap.context import RuntimeContext
from mellivor_kernel.bootstrap.exceptions import BootstrapError

__all__ = [
    "BootstrapBuilder",
    "BootstrapError",
    "KernelBootstrap",
    "RuntimeContext",
]
