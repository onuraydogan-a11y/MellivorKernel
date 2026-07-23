# Specifications

Detailed, subsystem-level specifications live here — one file (or subfolder)
per subsystem once its design is ready to be written down in full.

A spec goes deeper than the corresponding ADR: it defines concrete contracts,
data shapes, and behavior, rather than just the decision and its rationale.
Specs should reference the ADR(s) that motivated them.

Specs are added as each kernel subsystem is designed and implemented:

- [`core.md`](core.md)
- [`config.md`](config.md)
- [`providers.md`](providers.md)
- [`tools.md`](tools.md)
- [`bootstrap.md`](bootstrap.md)
- [`execution.md`](execution.md)
