"""Public API of the kernel's security foundation subsystem."""

from __future__ import annotations

from mellivor_kernel.security.audit import AuditRecord, AuditSink
from mellivor_kernel.security.contracts import SecureConfiguration, SecurityPolicy
from mellivor_kernel.security.env_secret_provider import EnvSecretProvider
from mellivor_kernel.security.exceptions import (
    SecretConfigurationError,
    SecretNotFoundError,
    SecretValueError,
    SecureConfigurationError,
    SecurityError,
)
from mellivor_kernel.security.policy import SecurityDecision
from mellivor_kernel.security.secrets import Secret, SecretProvider, SecretProviderRegistry

__all__ = [
    "AuditRecord",
    "AuditSink",
    "EnvSecretProvider",
    "Secret",
    "SecretConfigurationError",
    "SecretNotFoundError",
    "SecretProvider",
    "SecretProviderRegistry",
    "SecretValueError",
    "SecureConfiguration",
    "SecureConfigurationError",
    "SecurityDecision",
    "SecurityError",
    "SecurityPolicy",
]
