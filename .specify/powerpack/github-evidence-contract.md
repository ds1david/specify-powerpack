# POWERPACK GITHUB EVIDENCE ACQUISITION CONTRACT v1.2

Before technical judgment, the executor must acquire and verify through the
selected GitHub connector:

- repository and pull request number;
- base_ref, base_sha, merge_base and head_sha;
- immutable snapshot identity;
- complete changed_files[];
- complete diff and HEAD content for every changed file;
- active SPEC artifacts, including spec.md, plan.md, tasks.md, contracts and
  applicable checklists, architecture and constitution documents;
- related callers, callees, schemas, configuration, composition root, tests
  and contracts required to establish blast radius.

Listing a path or relying on a PR description is not file-content evidence.
The GitHub connector is the only PR/repository evidence source. Shell, local
checkout, web search, memory and author claims are not substitutes.

If any required item is unavailable, do not perform technical judgment. Return
one complete BLOCKED artifact and classify the gap as one or more of:

- MISSING_GITHUB_SNAPSHOT
- MISSING_CHANGED_FILES
- MISSING_CHANGED_FILE_CONTENTS
- MISSING_SPEC
- MISSING_TOOL
- INCOMPLETE_CONTEXT
