"""AIEngineBuilder: a fluent builder assembling the AI Engine Foundation
on top of an already-built RuntimeContext.
"""

from __future__ import annotations

from pathlib import Path

from mellivor_kernel.agents import AgentEngine
from mellivor_kernel.ai_engine.context import AIEngineContext
from mellivor_kernel.ai_engine.engine import AIEngine
from mellivor_kernel.ai_engine.exceptions import AIEngineError
from mellivor_kernel.authorization import AuthorizationEngine, PermissionResolver
from mellivor_kernel.bootstrap import RuntimeContext
from mellivor_kernel.core.logging import get_logger
from mellivor_kernel.events import EventBus
from mellivor_kernel.execution import Authorizer, Dispatcher, ExecutionEngine
from mellivor_kernel.memory import MemoryStore
from mellivor_kernel.observability import StructuredEventSink
from mellivor_kernel.plugin_discovery import PluginDiscovery
from mellivor_kernel.plugins import PluginLoader, PluginRegistry
from mellivor_kernel.security import AuditSink
from mellivor_kernel.workflow import WorkflowEngine


class AIEngineBuilder:
    """A fluent builder assembling the orchestration chain
    (`ExecutionEngine` -> `WorkflowEngine` -> `AgentEngine`, with an
    `Authorizer` optionally consulted) on top of an already-built
    `RuntimeContext`, plus a `PluginRegistry`.

    Every optional piece stays optional and explicit -- nothing here
    silently defaults infrastructure a caller didn't ask for, matching
    every composed engine's own `None`-means-disabled convention. All
    accumulated state is only assembled once, inside `build()` -- calling
    `with_*` methods in any order produces the same result, the same
    deferred-construction shape `BootstrapBuilder` already uses.
    """

    def __init__(self, runtime: RuntimeContext) -> None:
        """Initialize the builder.

        Args:
            runtime: The already-bootstrapped runtime to compose on top
                of. `AIEngineBuilder` never builds its own
                `RuntimeContext` -- that remains `bootstrap`'s
                responsibility.
        """
        self._runtime = runtime
        self._authorization_requested = False
        self._authorizer: Authorizer | None = None
        self._audit_sink: AuditSink | None = None
        self._event_bus: EventBus | None = None
        self._memory: MemoryStore | None = None
        self._observability: StructuredEventSink | None = None
        self._plugin_registry: PluginRegistry | None = None
        self._discovery_root: Path | str | None = None
        self._discovery_loader: PluginLoader | None = None

    def with_authorization(
        self, authorizer: Authorizer | None = None, *, audit_sink: AuditSink | None = None
    ) -> AIEngineBuilder:
        """Enable authorization for every execution request.

        Args:
            authorizer: The `Authorizer` to consult. If omitted, `build()`
                constructs a new `AuthorizationEngine` from the runtime's
                own `tool_registry`, using whatever `event_bus` was set
                by `build()` time.
            audit_sink: Consulted only when `authorizer` is omitted --
                wired into the default `AuthorizationEngine`, the same
                way Sprint 17 wired one in directly.

        Returns:
            This builder, for chaining.
        """
        self._authorization_requested = True
        self._authorizer = authorizer
        self._audit_sink = audit_sink
        return self

    def with_event_bus(self, event_bus: EventBus) -> AIEngineBuilder:
        """Publish lifecycle events from every composed engine to `event_bus`.

        Returns:
            This builder, for chaining.
        """
        self._event_bus = event_bus
        return self

    def with_memory(self, memory: MemoryStore) -> AIEngineBuilder:
        """Record execution/workflow/agent outcomes into `memory`.

        Returns:
            This builder, for chaining.
        """
        self._memory = memory
        return self

    def with_observability(self, sink: StructuredEventSink) -> AIEngineBuilder:
        """Emit `ExecutionEngine`'s structured observations to `sink`.

        Returns:
            This builder, for chaining.
        """
        self._observability = sink
        return self

    def with_plugin_registry(self, registry: PluginRegistry) -> AIEngineBuilder:
        """Use `registry` instead of a newly created, empty one.

        `registry` must not already be owned by another currently-live
        `AIEngine` -- `build()` raises `AIEngineError` if it is. Each
        `PluginRegistry` may back at most one live `AIEngine` at a time.

        Returns:
            This builder, for chaining.
        """
        self._plugin_registry = registry
        return self

    def with_plugin_discovery(
        self, root: Path | str, *, loader: PluginLoader | None = None
    ) -> AIEngineBuilder:
        """Discover and register every plugin under `root` during `build()`.

        Args:
            root: The filesystem location
                `PluginDiscovery.discover_and_register()` is called with.
            loader: The `PluginLoader` discovery uses. Defaults to a new
                `PluginLoader()` if not supplied.

        Returns:
            This builder, for chaining.
        """
        self._discovery_root = root
        self._discovery_loader = loader
        return self

    def build(self) -> AIEngine:
        """Assemble the AI Engine Foundation.

        Returns:
            The composed `AIEngine`.

        Raises:
            AIEngineError: If plugin discovery was requested and it
                raises, or if the resolved `PluginRegistry` is already
                owned by another currently-live `AIEngine`.
        """
        context = self._build_context()

        authorizer = self._authorizer
        if self._authorization_requested and authorizer is None:
            authorizer = AuthorizationEngine(
                PermissionResolver(self._runtime.tool_registry),
                event_bus=self._event_bus,
                audit_sink=self._audit_sink,
            )

        dispatcher = Dispatcher(self._runtime.tool_registry, self._runtime.provider_registry)
        execution_engine = ExecutionEngine(
            dispatcher,
            authorizer=authorizer,
            event_bus=self._event_bus,
            memory=self._memory,
            observability=self._observability,
        )
        workflow_engine = WorkflowEngine(
            execution_engine, memory=self._memory, event_bus=self._event_bus
        )
        agent_engine = AgentEngine(workflow_engine, memory=self._memory, event_bus=self._event_bus)

        plugin_registry = (
            self._plugin_registry if self._plugin_registry is not None else PluginRegistry()
        )
        if self._discovery_root is not None:
            loader = (
                self._discovery_loader if self._discovery_loader is not None else PluginLoader()
            )
            try:
                PluginDiscovery(loader).discover_and_register(self._discovery_root, plugin_registry)
            except Exception as exc:
                raise AIEngineError(
                    f"Plugin discovery from {self._discovery_root!r} failed: {exc}"
                ) from exc

        return AIEngine(
            runtime=self._runtime,
            context=context,
            execution_engine=execution_engine,
            workflow_engine=workflow_engine,
            agent_engine=agent_engine,
            authorizer=authorizer,
            plugin_registry=plugin_registry,
        )

    def _build_context(self) -> AIEngineContext:
        """Build the shared `AIEngineContext`.

        `RuntimeContext` deliberately never exposes the `Kernel` it
        wraps directly. This derives it from a legitimately-constructed
        `ExecutionContext`'s own public `.runtime` field -- the same
        object `RuntimeContext.execution_context()` already hands out --
        rather than requiring any change to `bootstrap`.
        """
        probe = self._runtime.execution_context(logger_name="ai_engine")
        return AIEngineContext(
            configuration=self._runtime.configuration,
            logger=get_logger("ai_engine"),
            runtime=probe.runtime,
            services=self._runtime.services,
        )
