"""ToolCallLoop: model-driven tool selection, executed by the kernel.

A consumer offers a model a set of kernel tools; the model decides which
to call; the loop runs each call through :class:`ExecutionEngine` (so
authorization, the tool pipeline, events, memory and observability all
stay in the path), feeds the results back, and repeats until the model
answers in text or the iteration budget runs out.

This is deliberately an execution-core component, not a provider one
and not an agent one:

- A provider only *describes* tools and *reports* calls
  (:mod:`mellivor_kernel.providers.tool_calling`); it never executes them.
- An :class:`~mellivor_kernel.agents.AgentDefinition` still runs one fixed
  workflow (ADR-0011). Nothing here changes that; a workflow step may
  wrap this loop later.
- The loop never stores conversation history. It receives ``messages``
  and returns the extended list; where that lives is the consumer's
  concern. Memory remains an audit record (ADR-0009).
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from mellivor_kernel.events import Event, EventBus
from mellivor_kernel.execution.context import ExecutionContext
from mellivor_kernel.execution.engine import ExecutionEngine
from mellivor_kernel.execution.events import (
    ToolCallCompleted,
    ToolCallRejected,
    ToolCallRequested,
)
from mellivor_kernel.execution.exceptions import ExecutionError
from mellivor_kernel.execution.request import ExecutionRequest, ExecutionTarget
from mellivor_kernel.providers.registry import ProviderRegistry
from mellivor_kernel.providers.tool_calling import (
    ToolCall,
    ToolResultBlock,
    ToolSpec,
    assistant_message,
    tool_results_message,
)
from mellivor_kernel.tools.registry import ToolRegistry

_DEFAULT_MAX_ITERATIONS = 8


class ToolLoopError(ExecutionError):
    """Raised when a :class:`ToolCallLoop` run cannot start."""


class ProviderCapabilityError(ToolLoopError):
    """Raised when the chosen provider does not declare tool-call support."""


@dataclass(frozen=True, slots=True)
class ToolCallDecision:
    """The answer of a ``before_tool_call`` hook.

    Attributes:
        allowed: Whether the call may run.
        reason: Why it was refused, when ``allowed`` is ``False``. Sent back
            to the model as an error result so it can respond accordingly.
    """

    allowed: bool
    reason: str | None = None


ALLOW = ToolCallDecision(allowed=True)


@dataclass(frozen=True, slots=True)
class ToolCallRecord:
    """One tool call the loop handled, for the caller's inspection.

    Attributes:
        call: The model's request.
        executed: Whether it reached the execution engine.
        success: Whether the tool succeeded (``False`` if not executed).
        result: The text returned to the model.
    """

    call: ToolCall
    executed: bool
    success: bool
    result: str


@dataclass(frozen=True, slots=True)
class ToolLoopResult:
    """The outcome of a :meth:`ToolCallLoop.run`.

    Attributes:
        success: Whether the model produced a final text answer.
        text: The final answer, or ``None`` if the loop ended otherwise.
        messages: The full message list after the run, including every
            assistant turn and tool result, so a caller can continue the
            conversation on a later turn.
        tool_calls: Every tool call the loop handled, in order.
        iterations: How many provider rounds ran.
        exhausted: ``True`` when the run stopped because ``max_iterations``
            was reached while the model still wanted tools.
        error: A human-readable failure description when ``success`` is
            ``False`` and the cause was not exhaustion.
    """

    success: bool
    text: str | None
    messages: tuple[Mapping[str, object], ...]
    tool_calls: tuple[ToolCallRecord, ...] = ()
    iterations: int = 0
    exhausted: bool = False
    error: str | None = None


@dataclass(frozen=True, slots=True)
class ToolLoopOptions:
    """Per-run settings for :class:`ToolCallLoop`.

    Attributes:
        max_iterations: The most provider rounds a run may take. A round
            that returns tool calls consumes one iteration; the run stops
            with ``exhausted=True`` rather than raising when the budget
            is spent.
        system: An optional system prompt forwarded to the provider.
        max_tokens: An optional ``max_tokens`` forwarded to the provider.
        before_tool_call: A hook consulted before each tool executes. The
            default allows everything. A refusal is reported to the model
            as an error result -- the seam a human-approval checkpoint
            can plug into without the loop knowing about approval.
    """

    max_iterations: int = _DEFAULT_MAX_ITERATIONS
    system: str | None = None
    max_tokens: int | None = None
    before_tool_call: Callable[[ToolCall], ToolCallDecision] = field(default=lambda call: ALLOW)

    def __post_init__(self) -> None:
        if self.max_iterations < 1:
            raise ToolLoopError("ToolLoopOptions.max_iterations must be at least 1.")


class ToolCallLoop:
    """Runs a model-with-tools conversation to a final answer."""

    def __init__(
        self,
        execution_engine: ExecutionEngine,
        tool_registry: ToolRegistry,
        provider_registry: ProviderRegistry,
        *,
        event_bus: EventBus | None = None,
    ) -> None:
        """Initialize the loop.

        Args:
            execution_engine: The engine every provider invocation and tool
                execution goes through. Its authorizer, memory, and
                observability apply unchanged.
            tool_registry: Where offered tool ids are resolved.
            provider_registry: Where the provider is resolved, to check
                that it declares tool-call support before any request.
            event_bus: The bus the loop's own events are published to. If
                ``None``, none are published.
        """
        self._engine = execution_engine
        self._tools = tool_registry
        self._providers = provider_registry
        self._event_bus = event_bus

    def run(
        self,
        provider_name: str,
        messages: Sequence[Mapping[str, object]],
        tool_ids: Sequence[str],
        context: ExecutionContext,
        *,
        options: ToolLoopOptions | None = None,
        granted_permissions: frozenset[str] = frozenset(),
    ) -> ToolLoopResult:
        """Run the conversation in ``messages`` until the model answers.

        Args:
            provider_name: The registered provider to converse with. It
                must declare ``supports_tool_calls``.
            messages: The conversation so far, in the provider-neutral
                shape. Must end with a user turn.
            tool_ids: The kernel tools the model may call. Only these are
                described to the model; a call for anything else is
                refused. An empty allowlist is a caller error -- use the
                provider directly for tool-free requests.
            context: The execution-lifetime context.
            options: Per-run settings; defaults apply if omitted.
            granted_permissions: Forwarded to the engine for each tool
                execution, exactly as for a direct ``execute`` call.

        Returns:
            A :class:`ToolLoopResult`. Provider failures and tool failures
            are reported in the result, never raised.

        Raises:
            ToolLoopError: If ``messages`` or ``tool_ids`` is empty, or a
                tool id is not registered.
            ProviderCapabilityError: If the provider is not registered or
                does not declare tool-call support.
        """
        opts = options if options is not None else ToolLoopOptions()
        if not messages:
            raise ToolLoopError("ToolCallLoop.run requires at least one message.")
        if not tool_ids:
            raise ToolLoopError(
                "ToolCallLoop.run requires a non-empty tool allowlist; "
                "invoke the provider directly for requests without tools."
            )
        specs = self._describe(tool_ids)
        self._require_tool_calls(provider_name)

        loop_id = str(uuid.uuid4())
        history: list[Mapping[str, object]] = list(messages)
        records: list[ToolCallRecord] = []
        allowed = frozenset(spec.name for spec in specs)
        iteration = 0

        while iteration < opts.max_iterations:
            iteration += 1
            response = self._engine.execute(
                ExecutionRequest(
                    target=ExecutionTarget.PROVIDER,
                    operation=provider_name,
                    payload=self._provider_payload(history, specs, opts),
                ),
                context,
            )
            if not response.success or response.payload is None:
                return ToolLoopResult(
                    success=False,
                    text=None,
                    messages=tuple(history),
                    tool_calls=tuple(records),
                    iterations=iteration,
                    error=response.error or "Provider returned no payload.",
                )
            text, calls = self._parse(response.payload)
            history.append(assistant_message(text, calls))
            if not calls:
                return ToolLoopResult(
                    success=True,
                    text=text,
                    messages=tuple(history),
                    tool_calls=tuple(records),
                    iterations=iteration,
                )
            results = [
                self._handle(
                    call, allowed, opts, context, granted_permissions, loop_id, iteration, records
                )
                for call in calls
            ]
            history.append(tool_results_message(results))

        return ToolLoopResult(
            success=False,
            text=None,
            messages=tuple(history),
            tool_calls=tuple(records),
            iterations=iteration,
            exhausted=True,
            error=(
                f"Tool loop stopped after {opts.max_iterations} iteration(s) "
                "without a final answer."
            ),
        )

    def _describe(self, tool_ids: Sequence[str]) -> tuple[ToolSpec, ...]:
        specs: list[ToolSpec] = []
        for tool_id in tool_ids:
            if not self._tools.exists(tool_id):
                raise ToolLoopError(f"Tool {tool_id!r} is not registered.")
            tool = self._tools.lookup(tool_id)
            specs.append(
                ToolSpec(
                    name=tool.id,
                    description=tool.description,
                    input_schema=tool.input_schema,
                )
            )
        return tuple(specs)

    def _require_tool_calls(self, provider_name: str) -> None:
        if not self._providers.is_registered(provider_name):
            raise ProviderCapabilityError(f"Provider {provider_name!r} is not registered.")
        if not self._providers.get(provider_name).capabilities.supports_tool_calls:
            raise ProviderCapabilityError(
                f"Provider {provider_name!r} does not declare supports_tool_calls."
            )

    @staticmethod
    def _provider_payload(
        history: Sequence[Mapping[str, object]],
        specs: Sequence[ToolSpec],
        opts: ToolLoopOptions,
    ) -> Mapping[str, object]:
        payload: dict[str, object] = {"messages": list(history), "tools": tuple(specs)}
        if opts.system is not None:
            payload["system"] = opts.system
        if opts.max_tokens is not None:
            payload["max_tokens"] = opts.max_tokens
        return payload

    @staticmethod
    def _parse(payload: Mapping[str, object]) -> tuple[str, tuple[ToolCall, ...]]:
        text = payload.get("text", "")
        if not isinstance(text, str):
            text = ""
        raw_calls = payload.get("tool_calls", ())
        calls: list[ToolCall] = []
        if isinstance(raw_calls, Sequence) and not isinstance(raw_calls, str | bytes):
            for entry in raw_calls:
                if isinstance(entry, ToolCall):
                    calls.append(entry)
        return text, tuple(calls)

    def _handle(
        self,
        call: ToolCall,
        allowed: frozenset[str],
        opts: ToolLoopOptions,
        context: ExecutionContext,
        granted_permissions: frozenset[str],
        loop_id: str,
        iteration: int,
        records: list[ToolCallRecord],
    ) -> ToolResultBlock:
        self._publish(
            ToolCallRequested(
                loop_id=loop_id, tool_call_id=call.id, tool_id=call.name, iteration=iteration
            )
        )
        if call.name not in allowed:
            return self._reject(call, "Tool is not in the offered set.", loop_id, records)
        decision = opts.before_tool_call(call)
        if not decision.allowed:
            return self._reject(call, decision.reason or "Tool call declined.", loop_id, records)

        outcome = self._engine.execute(
            ExecutionRequest(
                target=ExecutionTarget.TOOL, operation=call.name, payload=call.arguments
            ),
            context,
            granted_permissions=granted_permissions,
        )
        if outcome.success:
            rendered = _render(outcome.payload)
        else:
            rendered = outcome.error or "Tool execution failed."
        records.append(
            ToolCallRecord(call=call, executed=True, success=outcome.success, result=rendered)
        )
        self._publish(
            ToolCallCompleted(
                loop_id=loop_id, tool_call_id=call.id, tool_id=call.name, success=outcome.success
            )
        )
        return ToolResultBlock(tool_call_id=call.id, content=rendered, is_error=not outcome.success)

    def _reject(
        self, call: ToolCall, reason: str, loop_id: str, records: list[ToolCallRecord]
    ) -> ToolResultBlock:
        records.append(ToolCallRecord(call=call, executed=False, success=False, result=reason))
        self._publish(
            ToolCallRejected(
                loop_id=loop_id, tool_call_id=call.id, tool_id=call.name, reason=reason
            )
        )
        return ToolResultBlock(tool_call_id=call.id, content=reason, is_error=True)

    def _publish(self, event: Event) -> None:
        if self._event_bus is not None:
            self._event_bus.publish(event)


def _render(payload: Mapping[str, object] | None) -> str:
    """Render a tool's payload as text for the model."""
    if payload is None:
        return ""
    try:
        return json.dumps(dict(payload), ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(dict(payload))


__all__ = [
    "ALLOW",
    "ProviderCapabilityError",
    "ToolCallDecision",
    "ToolCallLoop",
    "ToolCallRecord",
    "ToolLoopError",
    "ToolLoopOptions",
    "ToolLoopResult",
]
