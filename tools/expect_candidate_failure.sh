#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/candidate"

set +e
python3 -m pytest tests/public/test_unit_contract.py 2>&1 | tee /tmp/workflow-recovery-unit-output.txt
status=${PIPESTATUS[0]}
set -e

if [ "$status" -eq 0 ]; then
  echo "candidate starter unexpectedly passed public unit tests"
  exit 1
fi

for expected in duplicate_external_start stale_state_misclassified missing_attempt_history unsafe_retry; do
  if ! grep -q "$expected" /tmp/workflow-recovery-unit-output.txt; then
    echo "public unit tests did not fail for expected reason: $expected"
    exit 1
  fi
done

echo "candidate starter failed public unit tests as expected"

