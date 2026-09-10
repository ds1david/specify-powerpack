# Checklist: No-Assumptions Target Acceptance

- [ ] CHK001 Exactly one delivery target is resolved before consequential checklist gating: `FULL_SPEC`, `CURRENT_PHASE`, `MVP_MIN`, or `MVP_MAX`.
- [ ] CHK002 Target membership is authoritative; priority, task order, PR title, implementation state, or reviewer preference cannot define it.
- [ ] CHK003 Every consequential checklist item is individually assigned `REQUIRED_NOW`, `EXPLICITLY_DEFERRED`, or `NOT_APPLICABLE_WITH_REASON`.
- [ ] CHK004 Every deferral cites an authoritative source; no item is deferred by assumption.
- [ ] CHK005 Every non-applicable item records concrete applicability reasoning/evidence.
- [ ] CHK006 Ambiguous target membership yields clarification/blocking, never inferred scope.
- [ ] CHK007 Every `REQUIRED_NOW` item receives an explicit semantic classification and evidence.
- [ ] CHK008 Application code/tests alone cannot prove a requirements-quality checklist item satisfied.
- [ ] CHK009 An item is marked `[x]` only after explicit evaluation against the selected target justifies satisfaction.
- [ ] CHK010 `CURRENT_PHASE` accepts only explicitly phase-assigned membership; later-phase items remain visible as authoritative deferrals.
- [ ] CHK011 `MVP_MIN` and `MVP_MAX` membership is explicitly defined; priority labels alone never create MVP scope.
- [ ] CHK012 Target/item decisions are persisted in JSON with authority/fingerprints and survive cross-session without ENV dependence.
- [ ] CHK013 Target-authority or item-content changes make affected prior decisions stale.
- [ ] CHK014 REQUIRED unresolved items cannot be bypassed through technical debt, backlog, TODO, or assumed future work.
- [ ] CHK015 `before_tasks` gates only after validating current target membership, item dispositions, semantic state, and freshness.
