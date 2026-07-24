"""Public API of the AI Engine Foundation.

A pure composition layer over an already-bootstrapped `RuntimeContext`
(`mellivor_kernel.bootstrap`) and the orchestration-chain engines
(`ExecutionEngine` -> `WorkflowEngine` -> `AgentEngine`, with an
`Authorizer` optionally consulted) plus a `PluginRegistry` -- introducing
no new business logic, chat features, prompting, reasoning, planning,
orchestration decisions, or provider-selection logic; see ADR-0018.

`AIEngine` is constructed only via `AIEngineBuilder.build()`. Every
operation delegates to the existing subsystem that already decides it --
`execute()`/`run_workflow()`/`run_agent()` call
`ExecutionEngine.execute()`/`WorkflowEngine.run()`/`AgentEngine.execute()`
exactly, with exactly the arguments given, and return exactly what that
engine returns. `bootstrap` remains solely responsible for infrastructure
assembly (`config`/`core`/`providers`/`tools`); this package never
duplicates that -- it only composes on top of an already-built
`RuntimeContext`.

`AIEngineContext` is deliberately not exported here: no supported code
path ever hands one to a consumer (`AIEngine`'s own context builders
return `ExecutionContext`/`WorkflowContext`/`AgentContext`/
`PluginContext`, never `AIEngineContext` itself), and it is only ever
constructed internally, by `AIEngineBuilder`.
"""

from __future__ import annotations

from mellivor_kernel.ai_engine.builder import AIEngineBuilder
from mellivor_kernel.ai_engine.engine import AIEngine
from mellivor_kernel.ai_engine.exceptions import AIEngineError

__all__ = [
    "AIEngine",
    "AIEngineBuilder",
    "AIEngineError",
]
