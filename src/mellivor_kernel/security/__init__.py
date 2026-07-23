"""Public API of the kernel's security foundation subsystem."""

from __future__ import annotations

from mellivor_kernel.security.audit import AuditRecord, AuditSink
from mellivor_kernel.security.contracts import SecureConfiguration, SecurityPolicy
from mellivor_kernel.security.exceptions import SecureConfigurationError, SecurityError
from mellivor_kernel.security.policy import SecurityDecision
from mellivor_kernel.security.secrets import Secret, SecretProvider, SecretProviderRegistry

__all__ = [
    "AuditRecord",
    "AuditSink",
    "Secret",
    "SecretProvider",
    "SecretProviderRegistry",
    "SecureConfiguration",
    "SecureConfigurationError",
    "SecurityDecision",
    "SecurityError",
    "SecurityPolicy",
]
