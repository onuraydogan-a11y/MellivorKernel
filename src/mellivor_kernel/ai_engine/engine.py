"""AIEngine: the composed AI Engine Foundation, delegating every operation
to the existing subsystem that already decides it.
"""

from __future__ import annotations

import weakref

from mellivor_kernel.agents import Agent, AgentContext, AgentEngine, AgentResult
from mellivor_kernel.ai_engine.context import AIEngineContext
from mellivor_kernel.ai_engine.exceptions import AIEngineError
from mellivor_kernel.bootstrap import RuntimeContext
from mellivor_kernel.core.logging import get_logger
from mellivor_kernel.execution import (
    Authorizer,
    ExecutionContext,
    ExecutionEngine,
    ExecutionRequest,
    ExecutionResult,
)
from mellivor_kernel.plugins import (
    PluginContext,
    PluginLifecycle,
    PluginLifecycleState,
    PluginRegistry,
)
from mellivor_kernel.workflow import Workflow, WorkflowContext, WorkflowEngine, WorkflowResult

# Tracks which live `AIEngine` currently owns a given `PluginRegistry`, so
# two engines can never drive independent, out-of-sync `PluginLifecycle`
# state machines against the same registered `Plugin` instances. Weak on
# both sides: an entry disappears on its own once either the registry or
# its owning engine is garbage collected -- ownership is never a
# permanent lock, only an exclusivity guarantee for as long as both are
# alive.
_registry_owners: weakref.WeakKeyDictionary[PluginRegistry, weakref.ReferenceType[AIEngine]] = (
    weakref.WeakKeyDictionary()
)


class AIEngine:
    """The composed AI Engine Foundation.

    A pure composition/delegation facade over an already-built
    `RuntimeContext` and the orchestration-chain engines
    (`ExecutionEngine` -> `WorkflowEngine` -> `AgentEngine`, with an
    `Authorizer` optionally consulted) plus a `PluginRegistry`.
    Constructed only by `AIEngineBuilder.build()` -- never directly.

    Introduces no new decision logic: `execute()`/`run_workflow()`/
    `run_agent()` call exactly the existing engine method they name,
    with exactly the arguments given, and return exactly what that
    engine returns. `AIEngine` does not manage the underlying `Kernel`'s
    own lifecycle -- that already happened once, inside
    `BootstrapBuilder.build()`, before this object ever existed. The one
    lifecycle `AIEngine` does own is the plugin fleet's
    (`start_plugins()`/`stop_plugins()`/`dispose_plugins()`), since a
    plugin is the only thing composed here with a defined lifecycle
    contract of its own.

    Exposes only `.runtime` and `.plugin_registry` -- never the composed
    `ExecutionEngine`/`WorkflowEngine`/`AgentEngine`/`Authorizer`
    themselves. Exposing those would let a caller permanently bypass
    `execute()`/`run_workflow()`/`run_agent()`, foreclosing any future
    ability to add engine-level behavior (metrics, additional guards)
    without a breaking change once external code depends on the direct
    path. `plugin_registry` stays public because it is not a bypass of
    any `AIEngine` method -- it is the object other code registers
    plugins into before calling `start_plugins()`.

    Each `PluginRegistry` this engine is built with may be owned by at
    most one live `AIEngine` at a time (enforced in `__init__`): sharing
    one registry across two engines would let each track that registry's
    plugins through its own independent `PluginLifecycle` objects,
    silently double-`initialize()`ing the same live `Plugin` instance the
    moment both engines call `start_plugins()`.
    """

    def __init__(
        self,
        *,
        runtime: RuntimeContext,
        context: AIEngineContext,
        execution_engine: ExecutionEngine,
        workflow_engine: WorkflowEngine,
        agent_engine: AgentEngine,
        authorizer: Authorizer | None,
        plugin_registry: PluginRegistry,
    ) -> None:
        """Initialize the engine. Not intended to be called directly --
        use `AIEngineBuilder.build()`.

        Raises:
            AIEngineError: If `plugin_registry` is already owned by
                another currently-live `AIEngine`.
        """
        existing_owner = _registry_owners.get(plugin_registry)
        if existing_owner is not None and existing_owner() is not None:
            raise AIEngineError(
                f"{plugin_registry!r} is already owned by another live AIEngine. "
                "Each AIEngine must be built with an exclusive PluginRegistry."
            )

        self._runtime = runtime
        self._context = context
        self._execution_engine = execution_engine
        self._workflow_engine = workflow_engine
        self._agent_engine = agent_engine
        self._authorizer = authorizer
        self._plugin_registry = plugin_registry
        self._plugin_lifecycles: dict[str, PluginLifecycle] = {}
        _registry_owners[plugin_registry] = weakref.ref(self)

    # -- composed subsystem access --------------------------------------------

    @property
    def runtime(self) -> RuntimeContext:
        """The already-bootstrapped runtime this engine composes on top of."""
        return self._runtime

    @property
    def plugin_registry(self) -> PluginRegistry:
        """The registry of plugins composed with this engine."""
        return self._plugin_registry

    # -- delegated operations --------------------------------------------------

    def execute(
        self,
        request: ExecutionRequest,
        context: ExecutionContext,
        *,
        granted_permissions: frozenset[str] = frozenset(),
    ) -> ExecutionResult:
        """Delegate to `ExecutionEngine.execute()` exactly.

        Args:
            request: The request to execute.
            context: The execution-lifetime context to execute with.
            granted_permissions: Forwarded unchanged.

        Returns:
            Exactly what `ExecutionEngine.execute()` returns.
        """
        return self._execution_engine.execute(
            request, context, granted_permissions=granted_permissions
        )

    def run_workflow(self, workflow: Workflow, context: WorkflowContext) -> WorkflowResult:
        """Delegate to `WorkflowEngine.run()` exactly.

        Returns:
            Exactly what `WorkflowEngine.run()` returns.
        """
        return self._workflow_engine.run(workflow, context)

    def run_agent(self, agent: Agent, context: AgentContext) -> AgentResult:
        """Delegate to `AgentEngine.execute()` exactly.

        Returns:
            Exactly what `AgentEngine.execute()` returns.
        """
        return self._agent_engine.execute(agent, context)

    # -- context builders -------------------------------------------------------

    def execution_context(self, *, logger_name: str = "execution") -> ExecutionContext:
        """Build an `ExecutionContext` for use with `execute()`."""
        return self._context.to_execution_context(logger=get_logger(logger_name))

    def workflow_context(self, *, logger_name: str = "workflow") -> WorkflowContext:
        """Build a `WorkflowContext` for use with `run_workflow()`."""
        return self._context.to_workflow_context(logger=get_logger(logger_name))

    def agent_context(self, *, logger_name: str = "agents") -> AgentContext:
        """Build an `AgentContext` for use with `run_agent()`."""
        return self._context.to_agent_context(logger=get_logger(logger_name))

    def plugin_context(self, *, logger_name: str = "plugins") -> PluginContext:
        """Build a `PluginContext` for use with a plugin's own lifecycle."""
        return self._context.to_plugin_context(logger=get_logger(logger_name))

    # -- plugin lifecycle ---------------------------------------------------------

    def start_plugins(self) -> None:
        """Initialize then start every plugin currently in `plugin_registry`.

        Re-reads `plugin_registry.enumerate()` on every call, so a plugin
        registered after this `AIEngine` was built is still picked up.
        Uses one `PluginLifecycle` per plugin id, held for the lifetime
        of this `AIEngine`, so `stop_plugins()`/`dispose_plugins()`
        operate on the same lifecycle state `start_plugins()` created.
        A plugin already past `PluginLifecycleState.REGISTERED` (for
        example one previously stopped by `stop_plugins()`) is only
        `start()`-ed again, not re-initialized -- `PluginLifecycle`
        itself only permits `initialize()` once, from `REGISTERED`.
        """
        context = self.plugin_context()
        for metadata in self._plugin_registry.enumerate():
            lifecycle = self._lifecycle_for(metadata.id)
            if lifecycle.state == PluginLifecycleState.REGISTERED:
                lifecycle.initialize(context)
            lifecycle.start()

    def stop_plugins(self) -> None:
        """Stop every plugin currently in `plugin_registry`."""
        for metadata in self._plugin_registry.enumerate():
            self._lifecycle_for(metadata.id).stop()

    def dispose_plugins(self) -> None:
        """Dispose every plugin currently in `plugin_registry`."""
        for metadata in self._plugin_registry.enumerate():
            self._lifecycle_for(metadata.id).dispose()

    def _lifecycle_for(self, plugin_id: str) -> PluginLifecycle:
        """Return this plugin's `PluginLifecycle`, creating it on first use."""
        if plugin_id not in self._plugin_lifecycles:
            self._plugin_lifecycles[plugin_id] = PluginLifecycle(
                self._plugin_registry.lookup(plugin_id)
            )
        return self._plugin_lifecycles[plugin_id]
