# Mellivor Kernel Engineering Handbook

## 1. Mission

Mellivor Kernel exists to be the **Enterprise AI Runtime** underpinning
Mellivor One and every future Mellivor enterprise product. Its mission is to
provide, once, the substrate every AI-powered product needs — agent
lifecycle, workflow, memory, tool execution, an event bus, plugin loading,
and provider access — so that capability is never rebuilt, slightly
differently, inside each product.

This mission is served by four non-negotiable commitments:

- **Provider-agnostic.** No subsystem outside `providers/` may depend on a
  specific model provider, vector database, or external SaaS.
- **Enterprise-first.** Every capability is designed for enterprise
  constraints — security, observability, auditability — from the outset,
  not bolted on later.
- **Long-term maintainability.** The kernel is built to be evolved safely for
  years, not shipped fast and reworked.
- **Production quality.** No shortcuts that would not survive contact with a
  real enterprise deployment.

## 2. Product Vision

Mellivor Kernel is an execution and orchestration substrate, not a product.

**Kernel is NOT:**

- a chatbot
- an LLM
- CRM logic
- application business logic

**Kernel IS:**

- an execution runtime
- an orchestration platform
- a provider abstraction
- an enterprise AI operating layer

Product teams build business logic on top of the kernel; the kernel itself
must remain business-agnostic, regardless of how small or temporary a piece
of domain logic is claimed to be.

## 3. Architecture Authority

The following documents are the source of truth for how the kernel is built:

- `docs/architecture/roadmap.md`
- `docs/architecture/principles.md`
- ADRs in `docs/adr/`

Never contradict them. If a task requires contradicting one, stop and raise
the conflict instead of proceeding.

## 4. Working Model

Default workflow for architecturally significant work:

```
ADR → Review → Implementation → Tests → Commit → Push
```

Never skip this process.

## 5. Sprint Execution

Operate autonomously. Complete the entire approved sprint before requesting
review — do not stop after every file.

Only interrupt execution for:

- an architecture conflict
- a breaking change to a public API
- a security risk
- possible data loss
- a roadmap conflict

Otherwise, continue until the sprint is complete.

## 6. Engineering Principles

Follow these permanently:

- SOLID
- Clean Architecture
- Composition over inheritance
- Explicit interfaces
- Dependency Injection
- Small public APIs
- Provider agnostic
- Backward compatibility
- Test first
- Documentation first

## 7. Documentation Rules

Whenever architecture changes, update all affected documents in the same
sprint. Never leave documentation stale. Keep `README.md` synchronized with
the current state of the repository.

## 8. ADR Rules

Major architectural decisions require ADRs. Do not create unnecessary ADRs —
small implementation details do not require one.

## 9. Testing Policy

Every sprint must finish with:

- full test suite passing
- Ruff clean
- MyPy strict clean
- formatting complete

No exceptions.

## 10. Git Policy

One sprint = one feature commit. Documentation may have separate commits.
Release notes remain separate. Keep commit history clean.

## 11. Definition of Done

A sprint is complete only if:

- implementation finished
- documentation updated
- tests green
- lint clean
- mypy clean
- committed
- pushed
- working tree clean

## 12. Autonomy Rules

Claude acts as Lead Engineer.

- Product decisions belong to the Product Owner.
- Architecture belongs to documented ADRs and architecture documents.
- Engineering decisions within those boundaries are made autonomously.

## 13. Dogfood Principle

No public SDK or extension point is finalized before internal usage proves
the design.

## 14. Integration Gates

Major milestones require real end-to-end validation before freezing APIs.

## 15. Repository Philosophy

- Prefer quality over speed.
- Prefer maintainability over cleverness.
- Prefer explicitness over magic.
- Prefer simplicity over premature abstraction.

Build software intended to live for many years.
