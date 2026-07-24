"""AI Engine exception hierarchy."""

from __future__ import annotations

from mellivor_kernel.core.exceptions import KernelError


class AIEngineError(KernelError):
    """Raised for `AIEngineBuilder`/`AIEngine` construction-time failures
    only (a wrapped plugin-discovery failure, or a `PluginRegistry`
    already owned by another live `AIEngine`).

    Never raised for a runtime failure of a composed engine --
    `execute()`, `run_workflow()`, and `run_agent()` propagate exactly
    what `ExecutionEngine`/`WorkflowEngine`/`AgentEngine` themselves
    raise or return, never re-wrapped.
    """
