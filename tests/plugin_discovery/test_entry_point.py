"""Tests for mellivor_kernel.plugin_discovery.entry_point."""

from __future__ import annotations

import pytest

from mellivor_kernel.plugin_discovery.entry_point import resolve_entry_point
from mellivor_kernel.plugin_discovery.exceptions import EntryPointError
from mellivor_kernel.plugins_builtin import SystemInfoPlugin


def test_resolves_a_real_class() -> None:
    factory = resolve_entry_point("mellivor_kernel.plugins_builtin.system_info:SystemInfoPlugin")

    assert factory is SystemInfoPlugin


def test_resolved_factory_constructs_an_instance() -> None:
    factory = resolve_entry_point("mellivor_kernel.plugins_builtin.system_info:SystemInfoPlugin")

    instance = factory()

    assert isinstance(instance, SystemInfoPlugin)


@pytest.mark.parametrize("malformed", ["no-colon-here", "module:", ":attribute", ""])
def test_rejects_malformed_entry_point_strings(malformed: str) -> None:
    with pytest.raises(EntryPointError):
        resolve_entry_point(malformed)


def test_unimportable_module_raises_entry_point_error() -> None:
    with pytest.raises(EntryPointError):
        resolve_entry_point("this_module_does_not_exist_anywhere:Whatever")


def test_missing_attribute_raises_entry_point_error() -> None:
    with pytest.raises(EntryPointError):
        resolve_entry_point("mellivor_kernel.plugins_builtin.system_info:NoSuchAttribute")


def test_non_callable_attribute_raises_entry_point_error() -> None:
    with pytest.raises(EntryPointError):
        resolve_entry_point("mellivor_kernel.plugin_discovery.discovery:DEFAULT_MANIFEST_FILENAME")
