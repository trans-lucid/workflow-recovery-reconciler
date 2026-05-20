#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/.."
EVAL_TARGET="${EVAL_TARGET:-$PWD/solution}" python3 -m pytest evaluator/tests_hidden

