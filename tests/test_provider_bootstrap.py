"""End-to-end test wiring ProviderFactory and ProviderRegistry together."""

from __future__ import annotations

from collections.abc import Mapping

from mellivor_kernel.providers import (
    BaseProvider,
    ProviderCapabilities,
    ProviderConfiguration,
    ProviderFactory,
    ProviderHealthCheck,
    ProviderRegistry,
)


class _FakeProvider(BaseProvider):
    @property
    def name(self) -> str:
        return self.configuration.provider_name

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(supports_streaming=True)

    def check_health(self) -> ProviderHealthCheck:
        return ProviderHealthCheck(healthy=True, provider_name=self.name)

    def invoke(self, request: Mapping[str, object]) -> Mapping[str, object]:
        return {"echo": request}


def test_factory_built_provider_can_be_registered_and_used() -> None:
    factory = ProviderFactory()
    factory.register_provider_type("fake", _FakeProvider)
    registry = ProviderRegistry()

    config = ProviderConfiguration(provider_name="fake", default_model="fake-1")
    provider = factory.create(config)
    registry.register(provider)

    resolved = registry.get("fake")
    assert resolved.check_health().healthy is True
    assert resolved.invoke({"prompt": "hi"}) == {"echo": {"prompt": "hi"}}
