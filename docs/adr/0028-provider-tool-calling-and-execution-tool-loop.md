# 0028. Provider tool calling and execution-layer tool loop

Status: Proposed
Date: 2026-09-17

## Context

Mellivor One needs an assistant where a user writes free text, the model
decides which kernel tool to call, the tool runs, and the model summarises
the result. That is the first concrete consumer need Sprint 41's
evidence gate asked for before any v1.x addition.

Before this ADR the kernel could not express it:

- `ProviderCapabilities.supports_tool_calls` existed as descriptive
  metadata with no behaviour behind it (its docstring said so).
- `ClaudeProvider.invoke()` accepted a single `prompt` string, sent no
  `tools`, and raised `ClaudeResponseError` on a response that contained a
  `tool_use` block but no text. `OpenAIProvider`/`LocalProvider` accepted a
  string-only message list and dropped `tool_calls` from responses.
- Tools were executed only when a caller named one by id in an
  `ExecutionRequest`; nothing let a model choose.
- `AgentDefinition` runs one fixed workflow and, per ADR-0011, does not
  choose or sequence dynamically.

Constraints: the v1.x provider and tool contracts are frozen (ADR-0005:
additive only in a MINOR); model-chosen tool execution must not bypass the
authorization and pipeline path that caller-chosen execution goes through
(ADR-0006, ADR-0007); memory stays an audit record, not chat history
(ADR-0009); Sprint 38's deferral of agent planning primitives stands.

## Decision

Tool calling is split across two existing layers; no new subsystem.

**Provider layer describes tools and reports calls; it never executes.**
`providers/tool_calling.py` defines SDK-free value types — `ToolSpec`
(name, description, JSON-Schema `input_schema`), `ToolCall` (id, name,
arguments), `ToolResultBlock` (tool_call_id, content, is_error) — and the
provider-neutral message shape: a message's `content` is a string or a
block list of `text` / `tool_use` / `tool_result` entries.
`BaseProvider.invoke()` keeps its `Mapping -> Mapping` signature; a
provider that sets `supports_tool_calls=True` reads `request["tools"]`
(a sequence of `ToolSpec`) and `request["messages"]` in the neutral shape,
and returns `response["tool_calls"]` (a tuple of `ToolCall`, possibly
empty) beside `text`, which may be empty when the model only asked for
tools. Each provider translates between the neutral shape and its wire
format. `ClaudeProvider`, `OpenAIProvider` and `LocalProvider` implement
this; OpenAI and Local share one private translation module because they
speak the same Chat Completions format. `LocalProvider`'s flag is opt-in
through `configuration.extra["supports_tool_calls"]`, since whether a
local server honours `tools` depends on the served model and server flags
the kernel cannot detect. `GeminiProvider` is unchanged (flag stays
`False`) until a consumer needs it.

**Execution layer owns the loop.** `execution/tool_loop.py` adds
`ToolCallLoop`. A caller passes a provider name, the conversation, and a
non-empty allowlist of registered tool ids. The loop describes exactly
those tools, invokes the provider through `ExecutionEngine`, and for each
returned `ToolCall` dispatches an ordinary
`ExecutionRequest(target=TOOL, operation=call.name, payload=call.arguments)`
through the same engine — so the configured authorizer, tool pipeline,
memory, event bus and observability sink apply unchanged. Results are
appended as `tool_result` blocks and the provider is invoked again, until
it answers in text or `max_iterations` (default 8) is spent, which is
reported as `exhausted=True`, not raised. Calls for tools outside the
allowlist, and calls a caller-supplied `before_tool_call` hook declines,
are refused before execution and returned to the model as error results,
so the model can finish rather than the run aborting. The loop publishes
`ToolCallRequested` / `ToolCallCompleted` / `ToolCallRejected` on the
execution event bus. It refuses, before any request, a provider whose
`supports_tool_calls` is `False`; the flag now has consequences.

**What stays where it was.** The loop returns the extended message list;
storing conversation history is the consumer's job. Prompt construction,
summarisation, and any approval policy are the consumer's job — the
`before_tool_call` hook is only the seam. `BaseTool` gains one optional,
non-abstract `input_schema` property (default `{"type": "object"}`) so
existing tools need no change; a tool offered to a model should override
it. `AgentDefinition` and ADR-0011 are untouched.

This ships in `1.3.0` as a MINOR release under ADR-0005: no abstract method
was added, no signature or type changed, nothing was removed. The one
behaviour change is that a provider response containing tool calls but no
text — previously an error — now returns `text=""` with the calls.

## Alternatives considered

- **Run the loop inside the provider.** Rejected: the provider would
  execute tools, bypassing authorization and the pipeline (ADR-0007), and
  every provider would reimplement the loop.
- **Run the loop inside `AgentDefinition`.** Rejected: ADR-0011 defines an
  agent as a fixed-workflow wrapper. Reopening that is Sprint 38's planning
  question, which no consumer has yet justified. A workflow step may wrap
  `ToolCallLoop` later without changing either.
- **Leave the loop to consumers.** Rejected: each would rebuild it and the
  authorization path would be theirs to forget.
- **A new abstract `invoke_with_tools()` on `BaseProvider`.** Rejected:
  breaks third-party providers and forces a MAJOR for an additive feature.
- **Adopt one vendor's message format as the kernel's.** Rejected in favour
  of the small neutral block shape; the reference layout is Anthropic-like
  because it is the most explicit, and each provider owns its translation.

## Consequences

- Consumers get model-driven tool use with the kernel's authorization and
  audit in the path by default, and a single hook to add approval.
- Tool authors who want a model to call their tool correctly must supply a
  real `input_schema`; the kernel does not enforce it.
- `supports_tool_calls` is now enforced by the loop. A third-party provider
  that claims it without reading `tools` will silently ignore them; that is
  the provider's bug, and the allowlist plus `max_iterations` bound the
  damage.
- OpenAI-format `tool_result` errors are conveyed by an `Error:` text
  prefix because the format has no error flag; Anthropic gets `is_error`.
- Streaming, parallel tool execution, Gemini tool calling, stored
  conversation history and approval policy are explicitly out of scope and
  wait for consumer evidence.
