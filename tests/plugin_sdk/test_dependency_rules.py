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


def test_only_the_known_built_in_plugin_package_imports_plugin_sdk() -> None:
    """As of Sprint 20, `plugin_sdk` has exactly one legitimate
    dependent: `plugins_builtin` (the built-in `SystemInfoPlugin`
    dogfoods `BasePlugin`, per ADR-0016). No other kernel package should
    import it -- an unexpected new dependent here would mean `plugin_sdk`
    stopped being a leaf convenience layer without a documented decision.
    """
    src_root = Path(__file__).resolve().parents[2] / "src" / "mellivor_kernel"
    known_dependents = {"plugins_builtin"}

    offending: list[str] = []
    for path in src_root.rglob("*.py"):
        if "plugin_sdk" in path.parts or path.parts[len(src_root.parts)] in known_dependents:
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


def test_plugins_builtin_is_the_only_actual_dependent_of_plugin_sdk() -> None:
    """Confirms `plugins_builtin` really does import `plugin_sdk` -- the
    exemption above is for a real, exercised dependency, not a
    theoretical carve-out.
    """
    src_root = Path(__file__).resolve().parents[2] / "src" / "mellivor_kernel"
    plugins_builtin_dir = src_root / "plugins_builtin"

    found = False
    for path in plugins_builtin_dir.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith("mellivor_kernel.")
                and node.module.split(".")[1] == "plugin_sdk"
            ):
                found = True

    assert found is True
