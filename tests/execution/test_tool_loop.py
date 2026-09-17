"""Tests for mellivor_kernel.execution.tool_loop."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import pytest

from mellivor_kernel.core import Kernel, ServiceContainer, get_logger
from mellivor_kernel.events import Event, InMemoryEventBus
from mellivor_kernel.execution import (
    Dispatcher,
    ExecutionContext,
    ExecutionEngine,
    ProviderCapabilityError,
    ToolCallCompleted,
    ToolCallDecision,
    ToolCallLoop,
    ToolCallRejected,
    ToolCallRequested,
    ToolLoopError,
    ToolLoopOptions,
)
from mellivor_kernel.providers import (
    BaseProvider,
    ProviderCapabilities,
    ProviderConfiguration,
    ProviderHealthCheck,
    ProviderRegistry,
    ToolCall,
    ToolSpec,
)
from mellivor_kernel.tools import ToolRegistry
from mellivor_kernel.tools.builtin import EchoTool


@dataclass
class _FakeSettings:
    log_level: str = "INFO"


class _ScriptedProvider(BaseProvider):
    """Returns pre-scripted responses in order and records each request."""

    def __init__(
        self,
        responses: list[Mapping[str, object]],
        *,
        supports_tool_calls: bool = True,
        provider_name: str = "scripted",
    ) -> None:
        super().__init__(ProviderConfiguration(provider_name=provider_name))
        self._responses = list(responses)
        self._supports = supports_tool_calls
        self._name = provider_name
        self.requests: list[Mapping[str, object]] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(supports_tool_calls=self._supports)

    def check_health(self) -> ProviderHealthCheck:
        return ProviderHealthCheck(healthy=True, provider_name=self.name)

    def invoke(self, request: Mapping[str, object]) -> Mapping[str, object]:
        self.requests.append(request)
        if not self._responses:
            raise RuntimeError("scripted provider ran out of responses")
        return self._responses.pop(0)


class _Collector:
    """An EventHandler that appends every event to a list."""

    def __init__(self, sink: list[Event]) -> None:
        self._sink = sink

    def handle(self, event: Event) -> None:
        self._sink.append(event)


class _FailingTool(EchoTool):
    """An echo tool whose execution always fails."""

    @property
    def id(self) -> str:
        return "failing"

    def execute(self, context, request):  # type: ignore[no-untyped-def,override]
        raise RuntimeError("boom")


@dataclass
class _Harness:
    loop: ToolCallLoop
    provider: _ScriptedProvider
    context: ExecutionContext
    bus: InMemoryEventBus
    events: list[Event] = field(default_factory=list)


def _text(text: str) -> Mapping[str, object]:
    return {"text": text, "tool_calls": ()}


def _calls(*calls: ToolCall, text: str = "") -> Mapping[str, object]:
    return {"text": text, "tool_calls": calls}


def _harness(responses: list[Mapping[str, object]], **provider_kwargs: object) -> _Harness:
    tools = ToolRegistry()
    tools.register(EchoTool())
    tools.register(_FailingTool())
    providers = ProviderRegistry()
    provider = _ScriptedProvider(responses, **provider_kwargs)  # type: ignore[arg-type]
    providers.register(provider)
    bus = InMemoryEventBus()
    engine = ExecutionEngine(Dispatcher(tools, providers))
    loop = ToolCallLoop(engine, tools, providers, event_bus=bus)
    settings = _FakeSettings()
    context = ExecutionContext(
        configuration=settings,  # type: ignore[arg-type]
        logger=get_logger("test_tool_loop"),
        runtime=Kernel(settings),  # type: ignore[arg-type]
        services=ServiceContainer(),
    )
    harness = _Harness(loop=loop, provider=provider, context=context, bus=bus)
    collector = _Collector(harness.events)
    for event_type in (ToolCallRequested, ToolCallCompleted, ToolCallRejected):
        bus.subscribe(event_type, collector)
    return harness


_USER = ({"role": "user", "content": "hi"},)


def test_returns_text_when_model_needs_no_tools() -> None:
    h = _harness([_text("hello")])

    result = h.loop.run("scripted", _USER, ["echo"], h.context)

    assert result.success is True
    assert result.text == "hello"
    assert result.iterations == 1
    assert result.tool_calls == ()
    assert result.messages[-1]["role"] == "assistant"


def test_offers_only_allowlisted_tools_as_specs() -> None:
    h = _harness([_text("ok")])

    h.loop.run("scripted", _USER, ["echo"], h.context)

    tools = h.provider.requests[0]["tools"]
    assert isinstance(tools, tuple)
    assert [spec.name for spec in tools] == ["echo"]
    assert isinstance(tools[0], ToolSpec)


def test_executes_tool_and_feeds_result_back() -> None:
    call = ToolCall(id="c1", name="echo", arguments={"message": "ping"})
    h = _harness([_calls(call, text="calling"), _text("done")])

    result = h.loop.run("scripted", _USER, ["echo"], h.context)

    assert result.success is True
    assert result.text == "done"
    assert result.iterations == 2
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].executed and result.tool_calls[0].success
    assert "ping" in result.tool_calls[0].result

    second = h.provider.requests[1]["messages"]
    assert isinstance(second, list)
    assert second[-2]["role"] == "assistant"
    assert second[-2]["content"][1]["type"] == "tool_use"
    assert second[-1]["role"] == "user"
    block = second[-1]["content"][0]
    assert block["type"] == "tool_result"
    assert block["tool_call_id"] == "c1"
    assert block["is_error"] is False

    assert [type(e) for e in h.events] == [ToolCallRequested, ToolCallCompleted]


def test_rejects_tool_outside_allowlist_without_executing() -> None:
    call = ToolCall(id="c1", name="not-offered")
    h = _harness([_calls(call), _text("fine")])

    result = h.loop.run("scripted", _USER, ["echo"], h.context)

    assert result.success is True
    record = result.tool_calls[0]
    assert record.executed is False
    block = h.provider.requests[1]["messages"][-1]["content"][0]  # type: ignore[index]
    assert block["is_error"] is True
    assert any(isinstance(e, ToolCallRejected) for e in h.events)


def test_before_tool_call_hook_can_decline() -> None:
    call = ToolCall(id="c1", name="echo", arguments={"message": "x"})
    h = _harness([_calls(call), _text("ok")])
    seen: list[ToolCall] = []

    def deny(candidate: ToolCall) -> ToolCallDecision:
        seen.append(candidate)
        return ToolCallDecision(allowed=False, reason="needs approval")

    result = h.loop.run(
        "scripted", _USER, ["echo"], h.context, options=ToolLoopOptions(before_tool_call=deny)
    )

    assert seen == [call]
    assert result.tool_calls[0].executed is False
    assert result.tool_calls[0].result == "needs approval"
    assert not any(isinstance(e, ToolCallCompleted) for e in h.events)


def test_stops_exhausted_when_model_keeps_calling_tools() -> None:
    call = ToolCall(id="c", name="echo", arguments={"message": "again"})
    h = _harness([_calls(call)] * 3)

    result = h.loop.run(
        "scripted", _USER, ["echo"], h.context, options=ToolLoopOptions(max_iterations=2)
    )

    assert result.success is False
    assert result.exhausted is True
    assert result.iterations == 2
    assert len(result.tool_calls) == 2
    assert len(h.provider.requests) == 2


def test_provider_failure_is_reported_not_raised() -> None:
    h = _harness([])  # provider raises on first invoke

    result = h.loop.run("scripted", _USER, ["echo"], h.context)

    assert result.success is False
    assert result.exhausted is False
    assert result.error is not None and "ran out" in result.error


def test_failed_tool_execution_is_returned_to_model_as_error() -> None:
    call = ToolCall(id="c1", name="failing", arguments={"message": "x"})
    h = _harness([_calls(call), _text("understood")])

    result = h.loop.run("scripted", _USER, ["failing"], h.context)

    record = result.tool_calls[0]
    block = h.provider.requests[1]["messages"][-1]["content"][0]  # type: ignore[index]
    assert result.success is True
    assert record.executed is True
    assert record.success is False
    assert "boom" in record.result
    assert block["is_error"] is True
    completed = [e for e in h.events if isinstance(e, ToolCallCompleted)]
    assert completed and completed[0].success is False


def test_forwards_system_and_max_tokens() -> None:
    h = _harness([_text("ok")])

    h.loop.run(
        "scripted",
        _USER,
        ["echo"],
        h.context,
        options=ToolLoopOptions(system="be brief", max_tokens=64),
    )

    assert h.provider.requests[0]["system"] == "be brief"
    assert h.provider.requests[0]["max_tokens"] == 64


def test_refuses_provider_without_tool_call_capability() -> None:
    h = _harness([_text("ok")], supports_tool_calls=False)

    with pytest.raises(ProviderCapabilityError):
        h.loop.run("scripted", _USER, ["echo"], h.context)
    assert h.provider.requests == []


def test_refuses_unknown_provider() -> None:
    h = _harness([_text("ok")])

    with pytest.raises(ProviderCapabilityError):
        h.loop.run("missing", _USER, ["echo"], h.context)


def test_refuses_empty_allowlist_and_unknown_tool() -> None:
    h = _harness([_text("ok")])

    with pytest.raises(ToolLoopError):
        h.loop.run("scripted", _USER, [], h.context)
    with pytest.raises(ToolLoopError):
        h.loop.run("scripted", _USER, ["nope"], h.context)


def test_refuses_empty_messages() -> None:
    h = _harness([_text("ok")])

    with pytest.raises(ToolLoopError):
        h.loop.run("scripted", (), ["echo"], h.context)


def test_options_reject_zero_iterations() -> None:
    with pytest.raises(ToolLoopError):
        ToolLoopOptions(max_iterations=0)


def test_does_not_mutate_caller_messages() -> None:
    call = ToolCall(id="c1", name="echo", arguments={"message": "m"})
    h = _harness([_calls(call), _text("ok")])
    original = [{"role": "user", "content": "hi"}]

    result = h.loop.run("scripted", original, ["echo"], h.context)

    assert len(original) == 1
    assert len(result.messages) == 4
