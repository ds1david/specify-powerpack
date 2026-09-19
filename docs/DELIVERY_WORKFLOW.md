# Delivery workflow

The workflow supports both greenfield start and mid-flight adoption.

```text
adopt
-> missing SDD phases
-> checklist-converge
-> analyze
-> implement if pending tasks
-> converge
   -> tasks changed -> implement -> converge
   -> unchanged -> review preparation
-> independent review
   -> any finding, including suggestion/nit/warning
      -> mandatory remediation
      -> update implementation/tests
      -> update project documentation
      -> update active SPEC artifacts
      -> converge
      -> republish exact HEAD
      -> review
   -> BLOCKED -> fail
   -> APPROVED with zero findings -> complete
```

Checklist convergence and implementation convergence are distinct loops. Checklist convergence validates requirements-quality artifacts. Spec Kit converge validates delivered code against spec, plan and tasks and appends missing implementation work.

Review convergence has a stricter zero-finding contract: once a valid finding is emitted, its severity or “suggestion” wording does not make it optional. It must be implemented and documented in both the project and active SPEC surfaces affected by the finding before the next review round.

Loop exhaustion is never success.
