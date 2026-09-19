#!/usr/bin/env bash
set -euo pipefail
target="\${*:-}"
if [[ -z "\${target// }" ]]; then
  echo "Usage: deliver.sh <existing-spec-id-or-feature-description>" >&2
  exit 2
fi
exec specify workflow run powerpack-delivery \
  --input "target=\${target}" \
  --input "integration=auto" \
  --input "script_runtime=sh"
