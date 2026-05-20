#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$ROOT/generated/main"
python3 -m pip install -e ".[test]" >/tmp/workflow-render-main-install.txt
set +e
python3 -m pytest tests/public/test_unit_contract.py 2>&1 | tee /tmp/workflow-render-main-unit-output.txt
status=${PIPESTATUS[0]}
set -e
if [ "$status" -eq 0 ]; then
  echo "rendered candidate main unexpectedly passed public unit tests"
  exit 1
fi
for expected in duplicate_external_start stale_state_misclassified missing_attempt_history unsafe_retry; do
  if ! grep -q "$expected" /tmp/workflow-render-main-unit-output.txt; then
    echo "rendered candidate main did not fail for expected reason: $expected"
    exit 1
  fi
done

cd "$ROOT/generated/solution"
python3 -m pip install -e ".[test]" >/tmp/workflow-render-solution-install.txt
EVAL_TARGET="$PWD/solution" python3 -m pytest tests/public/test_unit_contract.py solution/tests evaluator/tests_hidden

echo "rendered repo smoke validation passed"

