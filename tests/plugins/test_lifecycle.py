"""Tests for mellivor_kernel.plugins.lifecycle."""

from __future__ import annotations

import pytest

from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.plugins import (
    Plugin,
    PluginContext,
    PluginLifecycle,
    PluginLifecycleError,
    PluginLifecycleState,
    PluginMetadata,
)


class _FakeSettings:
    log_level = "INFO"


class _RecordingPlugin(Plugin):
    def __init__(self, *, fail_on: str | None = None) -> None:
        self.calls: list[str] = []
        self._fail_on = fail_on

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="recording", name="Recording Plugin", version="1.0.0", description=""
        )

    def initialize(self, context: PluginContext) -> None:
        self._maybe_fail("initialize")

    def start(self) -> None:
        self._maybe_fail("start")

    def stop(self) -> None:
        self._maybe_fail("stop")

    def dispose(self) -> None:
        self._maybe_fail("dispose")

    def _maybe_fail(self, call: str) -> None:
        self.calls.append(call)
        if call == self._fail_on:
            raise RuntimeError(f"{call} failed")


def _make_context() -> PluginContext:
    settings = _FakeSettings()
    return PluginContext(
        configuration=settings,
        logger=get_logger("test_plugin_lifecycle"),
        runtime=Kernel(settings),
        services=ServiceContainer(),
    )


def test_lifecycle_starts_registered() -> None:
    lifecycle = PluginLifecycle(_RecordingPlugin())

    assert lifecycle.state == PluginLifecycleState.REGISTERED


def test_full_lifecycle_sequence_succeeds() -> None:
    plugin = _RecordingPlugin()
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

    assert plugin.calls == ["initialize", "start", "stop", "dispose"]


def test_a_stopped_plugin_can_be_restarted() -> None:
    plugin = _RecordingPlugin()
    lifecycle = PluginLifecycle(plugin)
    lifecycle.initialize(_make_context())
    lifecycle.start()
    lifecycle.stop()

    lifecycle.start()

    assert lifecycle.state == PluginLifecycleState.RUNNING
    assert plugin.calls == ["initialize", "start", "stop", "start"]


def test_initialize_from_non_registered_state_raises() -> None:
    lifecycle = PluginLifecycle(_RecordingPlugin())
    lifecycle.initialize(_make_context())

    with pytest.raises(PluginLifecycleError):
        lifecycle.initialize(_make_context())


def test_start_before_initialize_raises() -> None:
    lifecycle = PluginLifecycle(_RecordingPlugin())

    with pytest.raises(PluginLifecycleError):
        lifecycle.start()


def test_stop_before_start_raises() -> None:
    lifecycle = PluginLifecycle(_RecordingPlugin())
    lifecycle.initialize(_make_context())

    with pytest.raises(PluginLifecycleError):
        lifecycle.stop()


def test_dispose_while_running_raises() -> None:
    lifecycle = PluginLifecycle(_RecordingPlugin())
    lifecycle.initialize(_make_context())
    lifecycle.start()

    with pytest.raises(PluginLifecycleError):
        lifecycle.dispose()

    assert lifecycle.state == PluginLifecycleState.RUNNING


def test_dispose_is_idempotent() -> None:
    lifecycle = PluginLifecycle(_RecordingPlugin())
    lifecycle.initialize(_make_context())
    lifecycle.dispose()

    lifecycle.dispose()  # must not raise

    assert lifecycle.state == PluginLifecycleState.DISPOSED


@pytest.mark.parametrize(
    "reach_state",
    [
        PluginLifecycleState.REGISTERED,
        PluginLifecycleState.INITIALIZED,
        PluginLifecycleState.STOPPED,
    ],
)
def test_dispose_is_allowed_from_every_non_running_state(
    reach_state: PluginLifecycleState,
) -> None:
    lifecycle = PluginLifecycle(_RecordingPlugin())
    if reach_state != PluginLifecycleState.REGISTERED:
        lifecycle.initialize(_make_context())
    if reach_state == PluginLifecycleState.STOPPED:
        lifecycle.start()
        lifecycle.stop()

    lifecycle.dispose()

    assert lifecycle.state == PluginLifecycleState.DISPOSED


def test_a_failing_initialize_transitions_to_failed_and_wraps_the_error() -> None:
    lifecycle = PluginLifecycle(_RecordingPlugin(fail_on="initialize"))

    with pytest.raises(PluginLifecycleError):
        lifecycle.initialize(_make_context())

    assert lifecycle.state == PluginLifecycleState.FAILED


def test_a_failing_start_transitions_to_failed_and_wraps_the_error() -> None:
    lifecycle = PluginLifecycle(_RecordingPlugin(fail_on="start"))
    lifecycle.initialize(_make_context())

    with pytest.raises(PluginLifecycleError):
        lifecycle.start()

    assert lifecycle.state == PluginLifecycleState.FAILED


def test_a_failing_stop_transitions_to_failed_and_wraps_the_error() -> None:
    lifecycle = PluginLifecycle(_RecordingPlugin(fail_on="stop"))
    lifecycle.initialize(_make_context())
    lifecycle.start()

    with pytest.raises(PluginLifecycleError):
        lifecycle.stop()

    assert lifecycle.state == PluginLifecycleState.FAILED


def test_a_failing_dispose_transitions_to_failed_and_wraps_the_error() -> None:
    lifecycle = PluginLifecycle(_RecordingPlugin(fail_on="dispose"))
    lifecycle.initialize(_make_context())

    with pytest.raises(PluginLifecycleError):
        lifecycle.dispose()

    assert lifecycle.state == PluginLifecycleState.FAILED


def test_dispose_is_allowed_from_failed_to_clean_up() -> None:
    lifecycle = PluginLifecycle(_RecordingPlugin(fail_on="start"))
    lifecycle.initialize(_make_context())
    with pytest.raises(PluginLifecycleError):
        lifecycle.start()
    state_after_failed_start = lifecycle.state
    assert state_after_failed_start == PluginLifecycleState.FAILED

    lifecycle.dispose()

    state_after_dispose = lifecycle.state
    assert state_after_dispose == PluginLifecycleState.DISPOSED


def test_lifecycle_exposes_the_wrapped_plugin() -> None:
    plugin = _RecordingPlugin()
    lifecycle = PluginLifecycle(plugin)

    assert lifecycle.plugin is plugin
