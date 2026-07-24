"""Dependency-boundary tests for Plugin Discovery.

`plugin_discovery` depends only on `plugins` (and, where needed, `core`)
-- never on `execution`, `providers`, `workflow`, `authorization`,
`memory`, `observability`, `security`, `bootstrap`, `plugin_sdk`, or
`plugins_builtin`. These tests prove that rule statically, and prove the
package introduces no dependency cycle.
"""

from __future__ import annotations

import ast
from pathlib import Path


def test_plugin_discovery_imports_cleanly_on_its_own() -> None:
    import mellivor_kernel.plugin_discovery as plugin_discovery

    assert plugin_discovery.__all__


def test_plugin_discovery_source_only_imports_plugins_and_core() -> None:
    """Static proof of the Sprint 21 dependency rule: `plugin_discovery`
    depends only on `plugins` and `core`, never on `execution`,
    `providers`, `workflow`, `authorization`, `memory`, `observability`,
    `security`, `bootstrap`, `plugin_sdk`, or `plugins_builtin`.
    """
    discovery_dir = (
        Path(__file__).resolve().parents[2] / "src" / "mellivor_kernel" / "plugin_discovery"
    )
    allowed_top_level_modules = {"core", "plugins", "plugin_discovery"}

    offending: list[str] = []
    for path in discovery_dir.glob("*.py"):
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


def test_no_kernel_package_imports_plugin_discovery() -> None:
    """`plugin_discovery` is a new leaf with no dependents -- nothing in
    the kernel itself should import it.
    """
    src_root = Path(__file__).resolve().parents[2] / "src" / "mellivor_kernel"

    offending: list[str] = []
    for path in src_root.rglob("*.py"):
        if "plugin_discovery" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith("mellivor_kernel.")
                and node.module.split(".")[1] == "plugin_discovery"
            ):
                offending.append(str(path))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if (
                        alias.name.startswith("mellivor_kernel.")
                        and alias.name.split(".")[1] == "plugin_discovery"
                    ):
                        offending.append(str(path))

    assert offending == []
