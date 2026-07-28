# Sprint 26 — Release Candidate Gate (Verification & Documentation Parity)

Audit date: 2026-07-28
Audited commit: `ffbb250fa6514c61bd5e74b7404cb89be5d63241` (`docs(release): ratify provider contract and public API freeze audit for v1.0`)
Branch: `main`
Remote status at audit start: `main` matched `origin/main`, working tree clean

## Scope

Per [ADR-0019](../adr/0019-release-readiness-and-scope-lock.md), this sprint
closes the two remaining open items in `v1.0-release-checklist.md`'s
"Release gate" section: running and recording the full verification gate
(Task A), and confirming documentation/examples parity with the
implementation (Task B). No source code, tests, or public API were changed.
No `Deferred to v1.1` or `Future research` item was scheduled or touched.

## Task A — Release Verification

Executed against the audited commit above, in a clean environment:

```text
Python 3.13.14
pytest 9.1.1 / ruff 0.16.0 / mypy 2.3.0 (compiled: yes)

$ pytest -q
717 passed in 10.13s

$ ruff check .
All checks passed!

$ ruff format --check .
311 files already formatted

$ mypy
Success: no issues found in 246 source files
```

All four gates are green with no warnings, skips, or `xfail`s. Results are
recorded in the "Verification Record" section of
[`v1.0-release-checklist.md`](v1.0-release-checklist.md).

## Task B — Documentation / Examples Parity Review

Compared against the current implementation (`src/mellivor_kernel/`, commit
above):

- **Public export parity.** Every package's `__init__.py` `__all__` was
  extracted programmatically (18 packages) and diffed against its
  corresponding `docs/specs/*.md` file. Seventeen of eighteen specs name
  every exported symbol. One gap found (see "Drift found and corrected"
  below).
- **README.md.** Repository layout block, "Status" section, and package
  count (18 packages under `src/mellivor_kernel/`, matching `ls -d
  src/mellivor_kernel/*/`) all agree with the current tree. No stale
  version reference — `0.13.0` matches `src/mellivor_kernel/version.py` and
  `v1.0-release-checklist.md`'s candidate line.
- **`docs/architecture.md` and `docs/architecture/roadmap.md`.** Both
  reflect the kernel through Sprint 23 (`OpenAIProvider`) and Sprint 24
  (ADR-0019 scope lock); the drift the 2026-07-23
  [`roadmap-gap-analysis`](roadmap-gap-analysis-2026-07-23.md) found against
  Sprint 15/16 was already corrected by
  [`release-audit-sprint16.md`](release-audit-sprint16.md), and no new drift
  has been introduced since (only two commits have landed since that audit,
  both documentation-only: the ADR-0019 scope lock and the Sprint 25 Public
  API Freeze Audit ratification).
- **`docs/architecture/principles.md`.** Unchanged, timeless, no drift
  possible against implementation.
- **`docs/specs/README.md`.** Index lists all 18 subsystem specs; all 18
  files exist.
- **`docs/adr/README.md`.** Index lists ADR-0001 through ADR-0019, matching
  every file present in `docs/adr/`.
- **`examples/README.md` and `examples/`.** All 8 example files described in
  the README exist on disk with matching descriptions; no undocumented
  example and no documented-but-missing example.
- **`docs/specs/providers.md`, `memory.md`, `security.md`, `observability.md`,
  `plugins.md`, `bootstrap.md`.** The Sprint 25 Public API Freeze Audit's
  claimed ratification sections are present in all six files, as recorded in
  `v1.0-release-checklist.md`.
- **Local Markdown links.** All 57 Markdown files in the repository were
  scanned for relative links; every local link target resolves. (The Sprint
  14 audit checked 140 links across a smaller doc set; this count differs
  because it's a distinct link-count methodology over a larger, current file
  set, not a regression.)

### Drift found and corrected

`docs/specs/observability.md`'s "No-op default behavior" section described
the package's no-op implementations only generically ("the package offers
no-op implementations") without naming the three concrete classes exported
in `observability.__all__`: `NoOpMetricsRecorder`, `NoOpTraceRecorder`, and
`NoOpStructuredEventSink`. This is the one gap the export-parity check
above found. Corrected by naming all three explicitly, with a one-clause
description of each drawn directly from their existing docstrings in
`src/mellivor_kernel/observability/noops.py` — no new behavior claimed, no
content unrelated to the existing implementation introduced.

No other drift was found. No other file was modified.

## Final Recommendation

Both remaining `v1.0-release-checklist.md` "Release gate" items are closed:
the full verification gate passes and is recorded, and documentation/
examples parity is confirmed (with the one drift item above corrected).
All five "Release gate" checklist items are now checked.

This closes the checklist's own definition of release-candidate readiness.
It does **not** itself declare `1.0.0` or a Release Candidate — per
ADR-0005 and ADR-0019, that remains a separate, deliberate decision to be
recorded in its own future ADR, made once this gate's completion is
reviewed and accepted.
