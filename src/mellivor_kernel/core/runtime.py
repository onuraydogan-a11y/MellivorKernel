"""Kernel runtime: bootstrap, lifecycle state, and health reporting."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from mellivor_kernel.core.container import ServiceContainer
from mellivor_kernel.core.contracts import KernelSettings
from mellivor_kernel.core.exceptions import StartupError
from mellivor_kernel.core.logging import configure_logging, get_logger


class KernelState(StrEnum):
    """The lifecycle state of a running kernel instance."""

    NOT_STARTED = "not_started"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class HealthStatus:
    """A point-in-time health report for a kernel instance.

    Attributes:
        healthy: Whether the kernel is currently considered healthy.
        state: The kernel's current lifecycle state.
        detail: A human-readable explanation, primarily populated when the
            kernel is not healthy.
    """

    healthy: bool
    state: KernelState
    detail: str = ""


class Kernel:
    """The Mellivor Kernel runtime.

    Owns a :class:`~mellivor_kernel.core.container.ServiceContainer` and
    manages the kernel's startup and shutdown lifecycle.
    """

    def __init__(
        self,
        settings: KernelSettings,
        container: ServiceContainer | None = None,
    ) -> None:
        """Initialize the kernel.

        Args:
            settings: The configuration the kernel runtime depends on.
            container: The service container to use. A new, empty
                container is created if one is not provided.
        """
        self._settings = settings
        self._container = container if container is not None else ServiceContainer()
        self._state = KernelState.NOT_STARTED
        self._failure_detail: str | None = None
        self._logger = get_logger(__name__)

    @property
    def container(self) -> ServiceContainer:
        """The kernel's service container."""
        return self._container

    @property
    def state(self) -> KernelState:
        """The kernel's current lifecycle state."""
        return self._state

    def start(self) -> None:
        """Run the kernel startup sequence.

        Startable from :attr:`KernelState.NOT_STARTED`,
        :attr:`KernelState.STOPPED`, or :attr:`KernelState.FAILED` (retry).
        On success, the kernel transitions to :attr:`KernelState.RUNNING`.

        Raises:
            StartupError: If the kernel is not in a startable state, or if
                startup fails for any other reason. On failure, the kernel
                transitions to :attr:`KernelState.FAILED`.
        """
        if self._state not in (
            KernelState.NOT_STARTED,
            KernelState.STOPPED,
            KernelState.FAILED,
        ):
            raise StartupError(f"Cannot start kernel from state {self._state.value!r}.")

        self._state = KernelState.STARTING
        self._failure_detail = None

        try:
            configure_logging(self._settings)
        except Exception as exc:
            self._state = KernelState.FAILED
            self._failure_detail = str(exc)
            raise StartupError(f"Kernel startup failed: {exc}") from exc

        self._state = KernelState.RUNNING
        self._logger.info("Kernel started.")

    def shutdown(self) -> None:
        """Run the kernel shutdown sequence.

        Idempotent: calling this while the kernel is not
        :attr:`KernelState.RUNNING` has no effect.
        """
        if self._state != KernelState.RUNNING:
            return

        self._state = KernelState.STOPPING
        self._logger.info("Kernel shutting down.")
        self._state = KernelState.STOPPED

    def health(self) -> HealthStatus:
        """Return the kernel's current health status.

        Returns:
            A :class:`HealthStatus` reflecting the kernel's current state.
        """
        if self._state == KernelState.RUNNING:
            return HealthStatus(healthy=True, state=self._state)
        if self._state == KernelState.FAILED:
            return HealthStatus(
                healthy=False,
                state=self._state,
                detail=self._failure_detail or "Kernel failed to start.",
            )
        return HealthStatus(
            healthy=False,
            state=self._state,
            detail=f"Kernel is not running (state={self._state.value}).",
        )
