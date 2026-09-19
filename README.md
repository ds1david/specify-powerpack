# Specify PowerPack

Specify PowerPack adds one public capability to GitHub Spec Kit:

speckit.powerpack.deliver

It can start a new feature or adopt an existing SPEC mid-flight and automate only the remaining lifecycle.

## Delivery flow

inspect/adopt
-> missing SDD phases only
-> checklist-converge
-> analyze (advisory freshness report)
-> implement
-> implement <-> converge until tasks.md is stable
-> prepare exact PR/HEAD
-> independent review
   -> findings -> remediate -> converge -> review
   -> APPROVED -> delivered

A manual sequence such as clarify -> plan -> checklist -> tasks -> analyze is adopted at the post-tasks checkpoint. Existing artifacts are preserved. PowerPack converges any reviewer-owned checklist, re-runs analyze because it has no durable success artifact, then continues with implementation.

## Script-runtime parity

The command ships Bash, PowerShell and Python launchers using the same scripts frontmatter mechanism as Spec Kit core commands. Spec Kit resolves {SCRIPT} according to the project's .specify/init-options.json selection: sh, ps, or py.

The custom powerpack-control workflow step is Python because workflow steps execute inside the Spec Kit Python engine; it is not a project shell helper.

See docs/ for architecture, adoption, checklist convergence, workflow, script runtime and review contracts.
