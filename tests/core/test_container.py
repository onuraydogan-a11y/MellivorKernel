"""Tests for mellivor_kernel.core.container."""

from __future__ import annotations

import pytest

from mellivor_kernel.core import ServiceContainer, ServiceRegistrationError


class _Greeter:
    def __init__(self, message: str = "hello") -> None:
        self.message = message


def test_resolve_returns_instance_built_by_factory() -> None:
    container = ServiceContainer()
    container.register(_Greeter, lambda: _Greeter("hi"))

    resolved = container.resolve(_Greeter)

    assert isinstance(resolved, _Greeter)
    assert resolved.message == "hi"


def test_singleton_factory_is_lazy_and_invoked_at_most_once() -> None:
    container = ServiceContainer()
    calls = 0

    def factory() -> _Greeter:
        nonlocal calls
        calls += 1
        return _Greeter()

    container.register(_Greeter, factory, singleton=True)

    assert calls == 0

    first = container.resolve(_Greeter)
    second = container.resolve(_Greeter)

    assert calls == 1
    assert first is second


def test_non_singleton_factory_is_invoked_on_every_resolve() -> None:
    container = ServiceContainer()
    calls = 0

    def factory() -> _Greeter:
        nonlocal calls
        calls += 1
        return _Greeter()

    container.register(_Greeter, factory, singleton=False)

    first = container.resolve(_Greeter)
    second = container.resolve(_Greeter)

    assert calls == 2
    assert first is not second


def test_register_instance_returns_exact_object_on_resolve() -> None:
    container = ServiceContainer()
    instance = _Greeter("registered")

    container.register_instance(_Greeter, instance)

    assert container.resolve(_Greeter) is instance


def test_register_twice_raises() -> None:
    container = ServiceContainer()
    container.register(_Greeter, _Greeter)

    with pytest.raises(ServiceRegistrationError):
        container.register(_Greeter, _Greeter)


def test_register_instance_after_register_raises() -> None:
    container = ServiceContainer()
    container.register(_Greeter, _Greeter)

    with pytest.raises(ServiceRegistrationError):
        container.register_instance(_Greeter, _Greeter())


def test_resolve_unregistered_service_raises() -> None:
    container = ServiceContainer()

    with pytest.raises(ServiceRegistrationError):
        container.resolve(_Greeter)


def test_is_registered() -> None:
    container = ServiceContainer()
    assert container.is_registered(_Greeter) is False

    container.register(_Greeter, _Greeter)

    assert container.is_registered(_Greeter) is True
