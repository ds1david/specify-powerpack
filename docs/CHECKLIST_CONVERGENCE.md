# Checklist convergence

Custom Spec Kit checklists are reviewer-owned requirements-quality artifacts. An unchecked item is a real pre-implementation gate, not an implementation task.

PowerPack adds an internal checklist-converge stage before analyze/implement.

For every unchecked item the agent must:

1. evaluate the criterion against current authoritative artifacts;
2. mark it checked only when those artifacts provide evidence of satisfaction;
3. otherwise repair the owning source artifact;
4. re-evaluate after the repair;
5. preserve wording, task IDs and completed task markers;
6. never approve in bulk and never ask the user to bypass the gate.

The stage loops with a finite budget and fails closed if unchecked items remain.

It is intentionally not a separate public command. speckit.powerpack.deliver remains the public product surface.
