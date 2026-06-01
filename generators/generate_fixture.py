#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


WORKFLOW_TYPES = ["workspace_create", "document_import", "deployment", "video_pipeline"]
COUNT_BY_ENTITY = {
    "low": 4,
    "medium": 12,
    "high": 36,
}


def load_profile(path: str | None) -> dict:
    if not path:
        return {}
    profile_path = Path(path)
    if not profile_path.exists():
        return {}
    return json.loads(profile_path.read_text())


def profile_seed(profile: dict, fallback: int) -> int:
    try:
        return int(profile.get("generator_seed") or fallback)
    except (TypeError, ValueError):
        return fallback


def scenario_profile(profile: dict) -> dict:
    value = profile.get("scenario_profile")
    return value if isinstance(value, dict) else {}


def profile_count(profile: dict, fallback: int) -> int:
    entity_count = str(scenario_profile(profile).get("entity_count") or "").lower()
    if entity_count in COUNT_BY_ENTITY:
        return COUNT_BY_ENTITY[entity_count]
    difficulty = str(profile.get("difficulty") or profile.get("difficulty_profile") or "").lower()
    if difficulty == "junior":
        return COUNT_BY_ENTITY["low"]
    if difficulty == "staff":
        return COUNT_BY_ENTITY["high"]
    return fallback


def failure_mode_for(profile: dict, index: int) -> str:
    mode = str(scenario_profile(profile).get("failure_modes") or "multi_step")
    if mode == "basic":
        return "duplicate_request" if index % 5 == 0 else "normal"
    if mode == "ambiguous":
        if index % 11 == 0:
            return "external_unknown"
        if index % 7 == 0:
            return "timeout_then_completed"
        if index % 5 == 0:
            return "non_retryable_external_error"
        if index % 4 == 0:
            return "replay_burst"
    if index % 6 == 0:
        return "timeout_then_reconcile"
    if index % 8 == 0:
        return "stale_without_external_truth"
    return "normal"


def expected_external_state(failure_mode: str) -> str:
    if failure_mode in {"timeout_then_completed", "timeout_then_reconcile"}:
        return "completed"
    if failure_mode == "external_unknown":
        return "unknown"
    if failure_mode == "non_retryable_external_error":
        return "non_retryable"
    return "running"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260520)
    parser.add_argument("--count", type=int, default=4)
    parser.add_argument("--profile", default=None)
    parser.add_argument("--out", default="candidate/fixtures/public/workflow_events.jsonl")
    args = parser.parse_args()

    profile = load_profile(args.profile)
    seed = profile_seed(profile, args.seed)
    count = profile_count(profile, args.count)
    rng = random.Random(seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as handle:
        for index in range(count):
            failure_mode = failure_mode_for(profile, index)
            record = {
                "request_key": f"generated-{seed}-{index}",
                "workflow_type": rng.choice(WORKFLOW_TYPES),
                "resource_id": f"resource-{index:03d}",
                "failure_mode": failure_mode,
                "expected_external_state": expected_external_state(failure_mode),
                "requires_reconciliation": failure_mode != "normal",
            }
            if failure_mode in {"replay_burst", "duplicate_request"}:
                record["duplicate_count"] = 2 + (index % 3)
            if failure_mode in {"stale_without_external_truth", "external_unknown", "timeout_then_completed"}:
                record["stale_after_seconds"] = 60
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    print(f"wrote {count} workflow events to {out}")


if __name__ == "__main__":
    main()
