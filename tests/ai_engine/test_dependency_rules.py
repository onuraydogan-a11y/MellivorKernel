"""Dependency-boundary tests for the AI Engine Foundation.

`ai_engine` depends only on `core`, `bootstrap`, `execution`,
`authorization`, `workflow`, `agents`, `memory`, `events`, `security`,
`observability`, `plugins`, and `plugin_discovery` -- never on `config`,
`providers`, `tools`, `plugin_sdk`, or `plugins_builtin` directly, and it
introduces no new business logic that would need those. These tests prove
that rule statically, and prove the package introduces no dependency
cycle: nothing else in the kernel imports `ai_engine`.
"""

from __future__ import annotations

import ast
from pathlib import Path


def test_ai_engine_imports_cleanly_on_its_own() -> None:
    import mellivor_kernel.ai_engine as ai_engine

    assert ai_engine.__all__


def test_ai_engine_source_only_imports_the_approved_packages() -> None:
    """Static proof of the Sprint 22 dependency rule: `ai_engine` depends
    only on `core`, `bootstrap`, `execution`, `authorization`, `workflow`,
    `agents`, `memory`, `events`, `security`, `observability`, `plugins`,
    and `plugin_discovery`.
    """
    ai_engine_dir = Path(__file__).resolve().parents[2] / "src" / "mellivor_kernel" / "ai_engine"
    allowed_top_level_modules = {
        "core",
        "bootstrap",
        "execution",
        "authorization",
        "workflow",
        "agents",
        "memory",
        "events",
        "security",
        "observability",
        "plugins",
        "plugin_discovery",
        "ai_engine",
    }

    offending: list[str] = []
    for path in ai_engine_dir.glob("*.py"):
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


def test_no_kernel_package_imports_ai_engine() -> None:
    """`ai_engine` is the top of the composition stack -- nothing else in
    the kernel should depend on it, only products built on top of it.
    """
    src_root = Path(__file__).resolve().parents[2] / "src" / "mellivor_kernel"

    offending: list[str] = []
    for path in src_root.rglob("*.py"):
        if "ai_engine" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith("mellivor_kernel.")
                and node.module.split(".")[1] == "ai_engine"
            ):
                offending.append(str(path))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if (
                        alias.name.startswith("mellivor_kernel.")
                        and alias.name.split(".")[1] == "ai_engine"
                    ):
                        offending.append(str(path))

    assert offending == []
