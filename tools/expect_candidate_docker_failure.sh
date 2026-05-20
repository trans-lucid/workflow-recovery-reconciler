#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/candidate"

docker compose config >/tmp/workflow-recovery-compose-config.txt
docker compose up -d

cleanup() {
  docker compose down -v
}
trap cleanup EXIT

make seed

set +e
python3 -m pytest tests/public/test_integration_workflow.py 2>&1 | tee /tmp/workflow-recovery-integration-output.txt
status=${PIPESTATUS[0]}
set -e

if [ "$status" -eq 0 ]; then
  echo "candidate starter unexpectedly passed Docker-backed public integration test"
  exit 1
fi

if ! grep -q "test_public_docker_workflow_path_uses_state_gateway_and_queue" /tmp/workflow-recovery-integration-output.txt; then
  echo "Docker-backed public integration test did not run"
  exit 1
fi

found=0
for expected in duplicate_external_start stale_state_misclassified missing_attempt_history unsafe_retry; do
  if grep -q "$expected" /tmp/workflow-recovery-integration-output.txt; then
    found=1
  fi
done

if [ "$found" -ne 1 ]; then
  echo "Docker-backed public integration test failed for an unexpected reason"
  exit 1
fi

make seed
EVAL_TARGET="$ROOT/solution" python3 -m pytest tests/public/test_integration_workflow.py

echo "candidate starter failed Docker-backed public integration test as expected, and solution passes it"

