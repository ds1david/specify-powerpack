# Architecture

PowerPack composes Spec Kit rather than replacing its SDD semantics.

Public command: speckit.powerpack.deliver
Workflow: powerpack-delivery
Structured workflow step: powerpack-control

The workflow owns orchestration. The custom step owns facts that need machine-readable output: adoption state, checklist counts, task fingerprints and independent-review results.

The active lifecycle calls upstream commands directly:

specify -> clarify -> plan -> [checklist] -> tasks -> checklist-converge -> analyze -> implement <-> converge -> review

Analyze remains advisory. PowerPack does not interpret analysis prose as a machine route back to an owning phase.

Converge remains authoritative for implementation reconciliation. PowerPack compares the byte hash of tasks.md before and after converge. Changed tasks mean implementation must run again.

The complete pre-rewrite repository is stored under backup/ for historical reference only. Active extension, workflow and step code never imports, loads, executes or resolves state/templates from it.
