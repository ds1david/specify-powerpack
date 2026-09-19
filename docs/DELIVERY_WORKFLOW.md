# Delivery workflow

The workflow supports both greenfield start and mid-flight adoption.

adopt
-> missing SDD phases
-> checklist-converge
-> analyze
-> implement if pending tasks
-> converge
   -> tasks changed -> implement -> converge
   -> unchanged -> review preparation
-> independent review
   -> CHANGES_REQUIRED -> remediation -> converge -> republish -> review
   -> BLOCKED -> fail
   -> APPROVED -> complete

Checklist convergence and implementation convergence are distinct loops. Checklist convergence validates requirements-quality artifacts. Spec Kit converge validates delivered code against spec, plan and tasks and appends missing implementation work.

Loop exhaustion is never success.
