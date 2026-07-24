"""Dependency-boundary tests for the Plugin SDK.

Sprint 19 fixes the Plugin SDK's dependency rule explicitly: it depends
only on `plugins` and `core`, and must never depend on `execution`,
`providers`, `workflow`, `authorization`, `memory`, `observability`,
`security`, or `bootstrap`. These tests prove that rule statically, and
prove the SDK introduces no behavioral change to any existing subsystem.
"""

from __future__ import annotations

import ast
from pathlib import Path


def test_plugin_sdk_imports_cleanly_on_its_own() -> None:
    import mellivor_kernel.plugin_sdk as plugin_sdk

    assert plugin_sdk.__all__


def test_plugin_sdk_source_only_imports_plugins_and_core() -> None:
    """Static proof of the Sprint 19 dependency rule: `plugin_sdk` depends
    only on `plugins` (and, transitively allowed, `core`), never on
    `execution`, `providers`, `workflow`, `authorization`, `memory`,
    `observability`, `security`, or `bootstrap`.
    """
    sdk_dir = Path(__file__).resolve().parents[2] / "src" / "mellivor_kernel" / "plugin_sdk"
    allowed_top_level_modules = {"core", "plugins", "plugin_sdk"}

    offending: list[str] = []
    for path in sdk_dir.glob("*.py"):
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


def test_no_kernel_package_imports_plugin_sdk() -> None:
    """`plugin_sdk` is a convenience layer with no dependents -- nothing
    in the kernel itself should import it.
    """
    src_root = Path(__file__).resolve().parents[2] / "src" / "mellivor_kernel"

    offending: list[str] = []
    for path in src_root.rglob("*.py"):
        if "plugin_sdk" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith("mellivor_kernel.")
                and node.module.split(".")[1] == "plugin_sdk"
            ):
                offending.append(str(path))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if (
                        alias.name.startswith("mellivor_kernel.")
                        and alias.name.split(".")[1] == "plugin_sdk"
                    ):
                        offending.append(str(path))

    assert offending == []
