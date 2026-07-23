"""Public API of the kernel's agent runtime.

Agent Runtime coordinates existing kernel subsystems -- it does not
replace them. It is orchestration only: an agent run always delegates
its one workflow entirely to
:class:`~mellivor_kernel.workflow.WorkflowEngine`, never touching a tool,
provider, or ``Dispatcher`` directly, and never calling
``ExecutionEngine`` directly either. The dependency chain is fixed in one
direction: Agent -> Workflow -> Execution -> Tool/Provider -- see
ADR-0011.

No planning, no reasoning, no reflection, no multi-agent composition at
this sprint's scope.
"""

from __future__ import annotations

from mellivor_kernel.agents.agent import Agent
from mellivor_kernel.agents.context import AgentContext
from mellivor_kernel.agents.definition import AgentDefinition
from mellivor_kernel.agents.engine import AgentEngine
from mellivor_kernel.agents.events import AgentCompleted, AgentFailed, AgentStarted
from mellivor_kernel.agents.exceptions import AgentError
from mellivor_kernel.agents.result import AgentResult

__all__ = [
    "Agent",
    "AgentCompleted",
    "AgentContext",
    "AgentDefinition",
    "AgentEngine",
    "AgentError",
    "AgentFailed",
    "AgentResult",
    "AgentStarted",
]
