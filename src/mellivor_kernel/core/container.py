"""A lightweight dependency injection container for the kernel."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, cast

from mellivor_kernel.core.exceptions import ServiceRegistrationError

T = TypeVar("T")


class ServiceContainer:
    """A lightweight, type-safe dependency injection container.

    Services are registered against a key type -- typically an abstract
    interface or a concrete class -- and resolved by that same type.
    Singleton factories are invoked lazily: at most once, on first
    resolution.
    """

    def __init__(self) -> None:
        """Initialize an empty container."""
        self._factories: dict[type[Any], Callable[[], Any]] = {}
        self._singletons: dict[type[Any], bool] = {}
        self._instances: dict[type[Any], Any] = {}

    def register(
        self,
        service_type: type[T],
        factory: Callable[[], T],
        *,
        singleton: bool = True,
    ) -> None:
        """Register a factory for a service type.

        Args:
            service_type: The type other code will use to look up this
                service.
            factory: A zero-argument callable that constructs the service.
            singleton: If ``True`` (the default), ``factory`` is invoked at
                most once and the result is cached and reused for every
                later resolution. If ``False``, a new instance is
                constructed on every :meth:`resolve` call.

        Raises:
            ServiceRegistrationError: If ``service_type`` is already
                registered.
        """
        if self.is_registered(service_type):
            raise ServiceRegistrationError(f"Service {service_type!r} is already registered.")
        self._factories[service_type] = factory
        self._singletons[service_type] = singleton

    def register_instance(self, service_type: type[T], instance: T) -> None:
        """Register an already-constructed instance as a singleton service.

        Args:
            service_type: The type other code will use to look up this
                service.
            instance: The instance returned for every resolution of
                ``service_type``.

        Raises:
            ServiceRegistrationError: If ``service_type`` is already
                registered.
        """
        if self.is_registered(service_type):
            raise ServiceRegistrationError(f"Service {service_type!r} is already registered.")
        self._instances[service_type] = instance
        self._singletons[service_type] = True

    def resolve(self, service_type: type[T]) -> T:
        """Resolve a service instance for ``service_type``.

        Args:
            service_type: The type to resolve.

        Returns:
            The resolved service instance.

        Raises:
            ServiceRegistrationError: If ``service_type`` has not been
                registered.
        """
        if service_type in self._instances:
            return cast(T, self._instances[service_type])

        try:
            factory = self._factories[service_type]
        except KeyError as exc:
            raise ServiceRegistrationError(f"Service {service_type!r} is not registered.") from exc

        instance = factory()
        if self._singletons[service_type]:
            self._instances[service_type] = instance
        return cast(T, instance)

    def is_registered(self, service_type: type[Any]) -> bool:
        """Return whether ``service_type`` has already been registered.

        Args:
            service_type: The type to check.

        Returns:
            ``True`` if ``service_type`` was registered via :meth:`register`
            or :meth:`register_instance`, ``False`` otherwise.
        """
        return service_type in self._factories or service_type in self._instances
