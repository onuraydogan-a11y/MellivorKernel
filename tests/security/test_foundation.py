from __future__ import annotations

from dataclasses import dataclass

from mellivor_kernel.security import (
    AuditRecord,
    Secret,
    SecretProviderRegistry,
    SecureConfigurationError,
    SecurityDecision,
    SecurityError,
)


class ExampleSecretProvider:
    def __init__(self) -> None:
        self._secrets = {"api_key": Secret("api_key", "super-secret")}

    def resolve(self, name: str) -> Secret:
        return self._secrets[name]


class ExamplePolicy:
    def evaluate(self, *, subject: str, action: str) -> SecurityDecision:
        return SecurityDecision(allowed=subject == "kernel", reason=f"{subject}:{action}")


@dataclass
class RecordingAuditSink:
    records: list[AuditRecord]

    def record(self, record: AuditRecord) -> None:
        self.records.append(record)


class ExampleConfiguration:
    def __init__(self) -> None:
        self._secrets = {"api_key": Secret("api_key", "super-secret")}
        self._values = {"region": "us-east-1"}

    def get_secret(self, key: str) -> Secret:
        return self._secrets[key]

    def get_value(self, key: str) -> object:
        return self._values[key]


def test_secret_masked_repr() -> None:
    secret = Secret("api_key", "super-secret")

    assert "super-secret" not in repr(secret)
    assert "api_key" in repr(secret)


def test_secret_provider_registry_resolves_known_secret() -> None:
    provider = ExampleSecretProvider()
    registry = SecretProviderRegistry()
    registry.register(provider)

    resolved = registry.resolve("api_key")

    assert resolved.name == "api_key"
    assert resolved.value == "super-secret"


def test_secret_provider_registry_rejects_unknown_secret() -> None:
    registry = SecretProviderRegistry()

    try:
        registry.resolve("missing")
    except SecurityError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("expected SecurityError")


def test_secure_configuration_returns_plain_and_secret_values() -> None:
    configuration = ExampleConfiguration()

    assert configuration.get_value("region") == "us-east-1"
    assert configuration.get_secret("api_key").name == "api_key"


def test_security_policy_and_audit_contracts_are_structural() -> None:
    policy = ExamplePolicy()
    sink = RecordingAuditSink([])

    decision = policy.evaluate(subject="kernel", action="read")
    record = AuditRecord(
        event="security.policy.evaluated",
        subject="kernel",
        action="read",
        decision=decision,
    )
    sink.record(record)

    assert decision.allowed is True
    assert sink.records[0].event == "security.policy.evaluated"


def test_secure_configuration_error_is_a_security_error() -> None:
    assert issubclass(SecureConfigurationError, SecurityError)
