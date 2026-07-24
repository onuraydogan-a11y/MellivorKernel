"""PluginLifecycle: enforces legal initialize/start/stop/dispose transitions
for a single Plugin instance.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum

from mellivor_kernel.plugins.base import Plugin
from mellivor_kernel.plugins.context import PluginContext
from mellivor_kernel.plugins.exceptions import PluginLifecycleError


class PluginLifecycleState(StrEnum):
    """The lifecycle state of a `PluginLifecycle`-managed plugin instance."""

    REGISTERED = "registered"
    INITIALIZED = "initialized"
    RUNNING = "running"
    STOPPED = "stopped"
    DISPOSED = "disposed"
    FAILED = "failed"


class PluginLifecycle:
    """Enforces legal state transitions for one `Plugin` instance's
    `initialize()`/`start()`/`stop()`/`dispose()` lifecycle.

    Mirrors `core.runtime.Kernel`'s own state-guarded `start()`/
    `shutdown()` sequence: an out-of-order call raises rather than
    silently doing the wrong thing, and an exception from the underlying
    plugin transitions this instance to `PluginLifecycleState.FAILED`
    rather than leaving the state ambiguous.
    """

    def __init__(self, plugin: Plugin) -> None:
        """Initialize the lifecycle wrapper.

        Args:
            plugin: The plugin instance this lifecycle manages, starting
                in `PluginLifecycleState.REGISTERED`.
        """
        self._plugin = plugin
        self._state = PluginLifecycleState.REGISTERED

    @property
    def plugin(self) -> Plugin:
        """The plugin instance this lifecycle manages."""
        return self._plugin

    @property
    def state(self) -> PluginLifecycleState:
        """This plugin's current lifecycle state."""
        return self._state

    def initialize(self, context: PluginContext) -> None:
        """Run `Plugin.initialize()`.

        Args:
            context: The kernel-scoped context to initialize the plugin
                with.

        Raises:
            PluginLifecycleError: If not currently
                `PluginLifecycleState.REGISTERED`, or if the underlying
                plugin's `initialize()` raises.
        """
        self._require(PluginLifecycleState.REGISTERED, action="initialize")
        self._run(lambda: self._plugin.initialize(context), PluginLifecycleState.INITIALIZED)

    def start(self) -> None:
        """Run `Plugin.start()`.

        Raises:
            PluginLifecycleError: If not currently
                `PluginLifecycleState.INITIALIZED` or
                `PluginLifecycleState.STOPPED`, or if the underlying
                plugin's `start()` raises.
        """
        self._require(
            PluginLifecycleState.INITIALIZED, PluginLifecycleState.STOPPED, action="start"
        )
        self._run(self._plugin.start, PluginLifecycleState.RUNNING)

    def stop(self) -> None:
        """Run `Plugin.stop()`.

        Raises:
            PluginLifecycleError: If not currently
                `PluginLifecycleState.RUNNING`, or if the underlying
                plugin's `stop()` raises.
        """
        self._require(PluginLifecycleState.RUNNING, action="stop")
        self._run(self._plugin.stop, PluginLifecycleState.STOPPED)

    def dispose(self) -> None:
        """Run `Plugin.dispose()`.

        Idempotent: calling this while already
        `PluginLifecycleState.DISPOSED` has no effect. A running plugin
        must be `stop()`ped first.

        Raises:
            PluginLifecycleError: If currently
                `PluginLifecycleState.RUNNING`, or if the underlying
                plugin's `dispose()` raises.
        """
        if self._state == PluginLifecycleState.DISPOSED:
            return
        self._require(
            PluginLifecycleState.REGISTERED,
            PluginLifecycleState.INITIALIZED,
            PluginLifecycleState.STOPPED,
            PluginLifecycleState.FAILED,
            action="dispose",
        )
        self._run(self._plugin.dispose, PluginLifecycleState.DISPOSED)

    def _require(self, *allowed: PluginLifecycleState, action: str) -> None:
        """Raise unless the current state is one of `allowed`."""
        if self._state not in allowed:
            raise PluginLifecycleError(
                f"Cannot {action} plugin {self._plugin.metadata.id!r} from state "
                f"{self._state.value!r}."
            )

    def _run(self, call: Callable[[], None], next_state: PluginLifecycleState) -> None:
        """Run `call`, advancing to `next_state` on success or `FAILED` on error."""
        try:
            call()
        except Exception as exc:
            self._state = PluginLifecycleState.FAILED
            raise PluginLifecycleError(
                f"Plugin {self._plugin.metadata.id!r} failed during lifecycle transition "
                f"to {next_state.value!r}: {exc}"
            ) from exc
        self._state = next_state
