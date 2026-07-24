"""Lifecycle integration tests: SystemInfoPlugin driven through PluginLifecycle."""

from __future__ import annotations

import pytest

from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.plugins import (
    PluginContext,
    PluginLifecycle,
    PluginLifecycleError,
    PluginLifecycleState,
)
from mellivor_kernel.plugins_builtin import SystemInfoPlugin


class _FakeSettings:
    log_level = "INFO"


def _make_context() -> PluginContext:
    settings = _FakeSettings()
    kernel = Kernel(settings)
    kernel.start()
    return PluginContext(
        configuration=settings,
        logger=get_logger("test_system_info_lifecycle"),
        runtime=kernel,
        services=ServiceContainer(),
    )


def test_full_lifecycle_sequence_succeeds() -> None:
    plugin = SystemInfoPlugin()
    lifecycle = PluginLifecycle(plugin)
    context = _make_context()

    lifecycle.initialize(context)
    state_after_initialize = lifecycle.state
    assert state_after_initialize == PluginLifecycleState.INITIALIZED

    lifecycle.start()
    state_after_start = lifecycle.state
    assert state_after_start == PluginLifecycleState.RUNNING

    lifecycle.stop()
    state_after_stop = lifecycle.state
    assert state_after_stop == PluginLifecycleState.STOPPED

    lifecycle.dispose()
    state_after_dispose = lifecycle.state
    assert state_after_dispose == PluginLifecycleState.DISPOSED


def test_collect_works_once_initialized_even_without_starting() -> None:
    """`start()` is a no-op for this plugin -- `collect()` must work
    right after `initialize()`, demonstrating `BasePlugin`'s
    override-only-what-you-need design.
    """
    plugin = SystemInfoPlugin()
    lifecycle = PluginLifecycle(plugin)

    lifecycle.initialize(_make_context())
    snapshot = plugin.collect()

    assert snapshot.kernel_version


def test_collect_before_initialize_raises() -> None:
    plugin = SystemInfoPlugin()

    with pytest.raises(PluginLifecycleError):
        plugin.collect()


def test_start_stop_and_dispose_are_no_ops_that_never_raise() -> None:
    plugin = SystemInfoPlugin()
    lifecycle = PluginLifecycle(plugin)
    lifecycle.initialize(_make_context())

    lifecycle.start()  # must not raise
    lifecycle.stop()  # must not raise
    lifecycle.dispose()  # must not raise

    assert lifecycle.state == PluginLifecycleState.DISPOSED


def test_a_stopped_plugin_can_be_restarted_and_still_collects() -> None:
    plugin = SystemInfoPlugin()
    lifecycle = PluginLifecycle(plugin)
    lifecycle.initialize(_make_context())
    lifecycle.start()
    lifecycle.stop()

    lifecycle.start()
    snapshot = plugin.collect()

    assert lifecycle.state == PluginLifecycleState.RUNNING
    assert snapshot.kernel_version
