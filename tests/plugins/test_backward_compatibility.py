"""Backward-compatibility tests for the plugin runtime foundation.

`plugins` was an empty package skeleton before this sprint (see
ADR-0002/ADR-0014). These tests prove introducing real content did not
change any existing subsystem's behavior: `plugins` depends only on
`core` (and the top-level `version` module) per this sprint's dependency
rules, no other subsystem was touched, and a bootstrapped runtime behaves
exactly as it did before `plugins` had any implementation.
"""

from __future__ import annotations

import ast
from pathlib import Path

from mellivor_kernel.bootstrap import BootstrapBuilder
from mellivor_kernel.config import load_config
from mellivor_kernel.core import KernelState


def test_plugins_package_imports_cleanly_on_its_own() -> None:
    import mellivor_kernel.plugins as plugins

    assert plugins.__all__


def test_plugins_source_only_imports_core_and_the_version_module() -> None:
    """Static proof of the Sprint 18 dependency rule: `plugins` depends
    only on `core` (Kernel abstractions) and the top-level `version`
    module, never on `providers`, `tools`, `execution`, `authorization`,
    `events`, `memory`, `workflow`, `agents`, `security`, or
    `observability`.
    """
    plugins_dir = Path(__file__).resolve().parents[2] / "src" / "mellivor_kernel" / "plugins"
    allowed_top_level_modules = {"core", "version", "plugins"}

    offending: list[str] = []
    for path in plugins_dir.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            module_name: str | None = None
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith("mellivor_kernel.")
            ):
                module_name = node.module.split(".")[1]
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("mellivor_kernel."):
                        module_name = alias.name.split(".")[1]
            if module_name is not None and module_name not in allowed_top_level_modules:
                offending.append(f"{path.name}: mellivor_kernel.{module_name}")

    assert offending == []


def test_bootstrap_is_unaffected_by_the_plugin_runtime_foundation() -> None:
    """`bootstrap` does not compose `plugins` (matching how it does not
    compose `execution`/`authorization`/`workflow`/`agents`/`security`/
    `observability` either) -- building a runtime must behave identically
    to every prior sprint.
    """
    config = load_config({"MELLIVOR_ENVIRONMENT": "test"})
    runtime = BootstrapBuilder(config).with_builtin_tools().build()

    assert runtime.state == KernelState.RUNNING
    assert not hasattr(runtime, "plugin_registry")
    assert not hasattr(runtime, "plugin_context")
