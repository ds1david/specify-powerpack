---
applyTo: "specs/**/*.md"
---

# SPEC authoring and review rules

- Treat each SPEC as independently reviewable against `main` unless the SPEC itself explicitly declares a hard dependency.
- Reuse contracts from another SPEC only as an implementation optimization unless dependency is essential to user-visible correctness. An independent SPEC must define its minimum behavioral contract locally.
- Distinguish defects from capability evolution. Reintroducing or adding behavior intentionally removed by an earlier accepted SPEC is a new capability, not automatically a bug fix.
- Keep requirements implementation-neutral where possible. Put exact data structures, algorithms, file layouts, defaults that require research, and migration mechanics in plan/research artifacts unless they are product-level invariants.
- When a SPEC adds an AI-agent capability, define semantic behavior and allowed effects independently from one agent's tool names.
- Define failure/blocking semantics explicitly. Do not convert unavailable evidence, exhausted budgets, missing decisions, stale state, or configuration drift into success.
- Specify cross-session state authority explicitly when workflow continuity is required; do not rely on agent memory or persistent shell environment.
- If another SPEC offers shared infrastructure, state that the implementation SHOULD reuse it when available, while preserving this SPEC's independently testable user-visible contract unless a hard dependency is intentional.
