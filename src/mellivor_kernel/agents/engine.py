"""AgentEngine: orchestrates a single agent run by invoking its workflow."""

from __future__ import annotations

from mellivor_kernel.agents.agent import Agent
from mellivor_kernel.agents.context import AgentContext
from mellivor_kernel.agents.events import AgentCompleted, AgentFailed, AgentStarted
from mellivor_kernel.agents.result import AgentResult
from mellivor_kernel.events import Event, EventBus
from mellivor_kernel.memory import MemoryEntry, MemoryStore
from mellivor_kernel.workflow import Workflow, WorkflowEngine


class AgentEngine:
    """Orchestrates a single :class:`Agent` run by invoking its workflow.

    Agent Runtime is orchestration only -- it coordinates existing kernel
    subsystems, it does not replace them. ``AgentEngine`` never touches a
    tool, provider, or ``Dispatcher`` directly, and never calls
    ``ExecutionEngine`` directly either: every run is delegated entirely
    to the injected :class:`~mellivor_kernel.workflow.WorkflowEngine`, the
    same way ``WorkflowEngine`` delegates every step to
    ``ExecutionEngine`` and nothing else. The dependency chain is fixed:
    Agent -> Workflow -> Execution -> Tool/Provider, one direction only.

    No planning, no reasoning, no reflection, no multi-agent composition
    -- an agent run always invokes exactly the one workflow its
    :class:`~mellivor_kernel.agents.definition.AgentDefinition` names.
    """

    def __init__(
        self,
        workflow_engine: WorkflowEngine,
        *,
        memory: MemoryStore | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        """Initialize the engine.

        All infrastructure is received via dependency injection --
        ``AgentEngine`` never constructs a ``WorkflowEngine``, a memory
        backend, or an event bus itself.

        Args:
            workflow_engine: The engine this agent's workflow is
                delegated to.
            memory: The store this agent run's own outcome is recorded to
                (in addition to whatever ``workflow_engine`` itself may
                record, if it has its own memory configured). If ``None``
                (the default), nothing is recorded at the agent level.
            event_bus: The bus lifecycle events are published to. If
                ``None`` (the default), no events are published.
        """
        self._workflow_engine = workflow_engine
        self._memory = memory
        self._event_bus = event_bus

    def execute(self, agent: Agent, context: AgentContext) -> AgentResult:
        """Run ``agent``'s workflow to completion.

        Args:
            agent: The agent run to execute.
            context: The context to run with.

        Returns:
            An :class:`AgentResult` mirroring the invoked workflow's own
            outcome.
        """
        definition = agent.definition
        logger = context.workflow_context.execution_context.logger
        logger.info("Starting agent %r (%r).", agent.agent_id, definition.name)
        self._publish(AgentStarted(agent_id=agent.agent_id, name=definition.name))

        workflow = Workflow(definition=definition.workflow)
        workflow_result = self._workflow_engine.run(workflow, context.workflow_context)

        if workflow_result.success:
            result = AgentResult(success=True, workflow_result=workflow_result)
            logger.info("Agent %r (%r) completed.", agent.agent_id, definition.name)
            self._publish(AgentCompleted(agent_id=agent.agent_id, name=definition.name))
        else:
            error = f"Workflow {definition.workflow.name!r} failed: {workflow_result.error}"
            result = AgentResult(success=False, workflow_result=workflow_result, error=error)
            logger.warning("Agent %r (%r) failed: %s", agent.agent_id, definition.name, error)
            self._publish(AgentFailed(agent_id=agent.agent_id, name=definition.name, error=error))

        self._remember(agent, result, context)
        return result

    def _publish(self, event: Event) -> None:
        """Publish ``event`` if an :class:`~mellivor_kernel.events.bus.EventBus` is configured."""
        if self._event_bus is not None:
            self._event_bus.publish(event)

    def _remember(self, agent: Agent, result: AgentResult, context: AgentContext) -> None:
        """Record ``result`` to memory if a
        :class:`~mellivor_kernel.memory.store.MemoryStore` is configured.

        Never raises: a memory backend failure is logged and swallowed
        rather than allowed to break the agent run.
        """
        if self._memory is None:
            return

        if result.success:
            content = f"Agent {agent.definition.name!r} completed successfully."
        else:
            content = f"Agent {agent.definition.name!r} failed: {result.error}"

        entry = MemoryEntry(
            id=agent.agent_id,
            content=content,
            tags=frozenset({"agent"}),
            metadata={"name": agent.definition.name, "success": result.success},
        )
        try:
            self._memory.add(entry)
        except Exception as exc:
            context.workflow_context.execution_context.logger.warning(
                "Failed to record agent %r to memory: %s", agent.agent_id, exc
            )
