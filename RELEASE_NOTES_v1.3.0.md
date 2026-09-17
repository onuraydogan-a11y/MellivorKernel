# Mellivor Kernel v1.3.0

Commit: this release commit (`release(v1.3): prepare Mellivor Kernel 1.3.0`)

Branch: `main`

Tag: `v1.3.0` — to be applied manually after Product Owner approval.

## Summary

Mellivor Kernel 1.3.0 is a backward-compatible MINOR release under ADR-0005.
Its capability addition is tool calling, governed by ADR-0028: a model may
choose which kernel tools to call, and the kernel executes those calls
through its existing authorization and tool-pipeline path. The first
consumer is the Mellivor One assistant. No existing v1.2 public contract
changed.

## Public additions

- `providers.tool_calling`: `ToolSpec`, `ToolCall`, `ToolResultBlock`,
  `ToolCallingError`, `assistant_message`, `tool_results_message`
  (also exported from `mellivor_kernel.providers`)
- `execution.tool_loop`: `ToolCallLoop`, `ToolLoopOptions`,
  `ToolLoopResult`, `ToolCallRecord`, `ToolCallDecision`, `ALLOW`,
  `ToolLoopError`, `ProviderCapabilityError`
  (also exported from `mellivor_kernel.execution`)
- Execution events `ToolCallRequested`, `ToolCallCompleted`,
  `ToolCallRejected`
- `BaseTool.input_schema` — optional, non-abstract
- Tool calling in `ClaudeProvider`, `OpenAIProvider`, `LocalProvider`

## Dependencies

Unchanged. The base package still has no runtime dependency; the provider
extras are as in 1.2.0. No new extra was added.

## Compatibility and validation scope

- `BaseProvider.invoke()` keeps its signature. `{"prompt": ...}` callers
  and string-content `{"messages": ...}` callers behave exactly as before,
  except that the response mapping now also carries `tool_calls: ()`.
- A provider response that contains tool calls but no text used to raise
  the provider's "no text content" error; it now returns `text=""` with
  the calls. Only the previous error path is affected.
- `supports_tool_calls` is now enforced: `ToolCallLoop` refuses a provider
  that does not set it, before any request. `GeminiProvider` does not set
  it. `LocalProvider` sets it only when
  `ProviderConfiguration.extra["supports_tool_calls"]` is truthy, because
  whether an OpenAI-compatible server honours `tools` depends on the served
  model and server flags the kernel cannot detect.
- Validation is deterministic: fake clients for Claude and OpenAI, a mock
  HTTP transport for Local, and a scripted provider for the loop. No live
  API was exercised. Interoperability with a particular model, Ollama,
  LM Studio, or vLLM build is not claimed.

## Security and trust boundary

A model-chosen tool call runs as an ordinary
`ExecutionRequest(target=TOOL)` through `ExecutionEngine`: the configured
authorizer, `ToolExecutionPipeline` permission check, memory record, event
bus and observability sink apply unchanged. The model only sees the tools
the caller allowlists; a call for anything else is refused and reported
back to the model as an error result. `max_iterations` bounds every run.
The `before_tool_call` hook lets a consumer interpose approval; the kernel
ships no approval policy.

## Upgrade from v1.2.0

No consumer migration is required. To use tool calling:

1. Give each tool you will offer a real `input_schema`.
2. Build a `ToolCallLoop` over your `ExecutionEngine`, tool registry and
   provider registry.
3. Call `run(provider_name, messages, tool_ids, context)`; keep the
   returned `messages` yourself for the next turn.

See `examples/execution_tool_call_loop.py`.

## Intentionally excluded

Streaming, parallel tool execution, Gemini tool calling, stored
conversation history, prompt construction, and approval policy. Each waits
for consumer evidence per Sprint 41.
