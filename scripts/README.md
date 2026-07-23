# scripts

Developer and maintenance scripts (setup, linting, release tooling).

- [`smoke_test_claude_provider.py`](smoke_test_claude_provider.py) — a
  manual smoke test that makes a **real** call to the Anthropic API
  through the complete kernel stack (`ExecutionEngine` → `Dispatcher` →
  `ClaudeProvider`). Not part of the automated suite and never run in CI
  — it costs real tokens. Requires
  `pip install mellivor-kernel[anthropic]` and `ANTHROPIC_API_KEY` set:

  ```bash
  ANTHROPIC_API_KEY=sk-ant-... python scripts/smoke_test_claude_provider.py
  ```
