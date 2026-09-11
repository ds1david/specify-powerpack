# Checklist: PR Review Gate Enforcement

- [ ] PR review target is explicit and authoritative.
- [ ] Every accepted finding maps to current-target work or is reclassified with explicit out-of-target evidence.
- [ ] Any remaining accepted finding implies `REQUEST_CHANGES` when formal GitHub review submission is available.
- [ ] Severity does not make any accepted finding optional.
- [ ] No finding is closed as technical debt/backlog/TODO/future issue/future SPEC.
- [ ] Every accepted finding requiring implementation or verification is represented in `tasks.md`.
- [ ] Requirements-quality/coverage/ambiguity findings update checklist or authoritative requirements artifacts when applicable.
- [ ] Repair work is complete before a finding is considered for closure.
- [ ] All repaired findings are re-evaluated on the fresh immutable snapshot.
- [ ] Final `APPROVE` has zero unresolved findings and no missing mandatory acceptance evidence.
