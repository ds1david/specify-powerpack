# Delivery workflow

The workflow supports both greenfield start and mid-flight adoption.

```text
adopt
-> missing SDD phases
-> checklist-converge
-> analyze
-> validate plan.md + tasks.md execution contract
-> speckit.implement
     -> phase-by-phase
     -> dependencies first
     -> [P] tasks may run in parallel
     -> same-file/dependent tasks stay sequential
-> validate zero pending tasks
-> converge
   -> tasks changed/appended
      -> validate task plan
      -> speckit.implement with same phase/[P] rules
      -> converge
   -> unchanged -> review preparation
-> independent review
   -> any finding, including suggestion/nit/warning
      -> materialize mandatory remediation tasks
      -> update active SPEC traceability
      -> validate phase/dependency/[P] structure
      -> speckit.implement
      -> converge
      -> republish exact HEAD
      -> review
   -> BLOCKED -> fail
   -> APPROVED with zero findings -> complete
```

## Implementation authority

PowerPack deliberately does not parallelize workflow steps per task. The upstream `speckit.implement` command already owns the correct implementation semantics:

- complete phases in order;
- respect task dependencies;
- run test tasks before their corresponding implementation tasks when the task plan requests TDD;
- allow tasks explicitly marked `[P]` to execute together;
- serialize tasks that affect the same files;
- validate phase completion;
- mark completed tasks `[X]`.

PowerPack validates the structure before and after every implementation invocation and fails closed when implementation returns with pending tasks.

Checklist convergence and implementation convergence are distinct loops. Checklist convergence validates requirements-quality artifacts. Spec Kit converge validates delivered code against spec, plan and tasks and appends missing implementation work.

Review convergence has a zero-finding contract. Review remediation no longer patches product code directly: it first creates dependency-correct tasks and then delegates execution to `speckit.implement`.

Loop exhaustion is never success.
