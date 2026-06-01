#!/usr/bin/env python3
"""Validate that template personalization is declared, safe, and non-doc-only."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "translucid-template.json"
CONTEXT = ROOT / "template_context.json"
GENERATED = ROOT / "generated"
MAIN = GENERATED / "main"
SOLUTION = GENERATED / "solution"

REQUIRED_CUES = [
    "focus being evaluated",
    "expected failure classes",
    "hidden test intent",
    "scoring rubric",
    "debrief answer cues",
]


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def write_context(profile: dict) -> None:
    CONTEXT.write_text(json.dumps(profile, indent=2, sort_keys=True) + "\n")


def run_render() -> None:
    subprocess.run([sys.executable, "tools/render_template.py"], cwd=ROOT, check=True)


def read_texts(root: Path) -> str:
    chunks: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix in {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".pt", ".bin"}:
            continue
        try:
            chunks.append(path.read_text(errors="ignore"))
        except UnicodeDecodeError:
            continue
    return "\n".join(chunks)


def assert_candidate_safe(manifest: dict) -> None:
    forbidden_paths = manifest.get("candidate_main_forbidden_paths", [])
    for forbidden in forbidden_paths:
        if (MAIN / forbidden).exists():
            raise AssertionError(f"candidate main leaked forbidden path: {forbidden}")
    text = read_texts(MAIN)
    markers = manifest.get("personalization_contract", {}).get("candidate_forbidden_markers", [])
    for marker in markers:
        if marker and marker in text:
            raise AssertionError(f"candidate main leaked forbidden marker: {marker}")
    if "## Personalized Context" in text:
        raise AssertionError("candidate main leaked raw personalized context heading")
    if "hidden_test_emphasis" in text:
        raise AssertionError("candidate main leaked hidden-test personalization emphasis")


def assert_candidate_personalized(profile: dict) -> dict:
    readme = (MAIN / "README.md").read_text()
    expected = [profile["difficulty"], profile["company_name"], profile["selected_option"]["focus"]]
    for value in expected:
        if value not in readme:
            raise AssertionError(f"candidate README missing safe personalization value: {value}")
    profile_path = MAIN / "fixtures" / "public" / "personalization_profile.json"
    if not profile_path.exists():
        raise AssertionError("missing candidate personalization profile artifact")
    payload = json.loads(profile_path.read_text())
    if payload.get("difficulty") != profile["difficulty"]:
        raise AssertionError("profile artifact difficulty does not match selected profile")
    if payload.get("focus") != profile["selected_option"]["focus"]:
        raise AssertionError("profile artifact focus does not match selected profile")
    if "hidden_strictness" not in payload.get("scenario_knobs", {}):
        raise AssertionError("profile artifact missing hidden_strictness scenario knob")
    return payload


def assert_solution_cues(manifest: dict, profile: dict) -> None:
    note = SOLUTION / "PERSONALIZATION.md"
    if not note.exists():
        raise AssertionError("generated solution is missing private personalization notes")
    text = note.read_text().lower()
    for cue in manifest.get("personalization_contract", {}).get("solution_cue_requirements", REQUIRED_CUES):
        if cue.lower() not in text:
            raise AssertionError(f"solution personalization notes missing cue: {cue}")
    if profile["difficulty"] not in note.read_text():
        raise AssertionError("solution personalization notes missing selected difficulty")


def profile_for(difficulty: str, focus: str, seed: int, entity_count: str) -> dict:
    return {
        "company_name": "AcmeOps",
        "challenge_title": f"{difficulty.title()} Factory Validation Challenge",
        "role": "Backend Engineer" if difficulty != "staff" else "Staff Engineer",
        "time_limit": "60 min" if difficulty == "junior" else "120 min" if difficulty == "staff" else "90 min",
        "theme": f"{difficulty.title()} scenario for AcmeOps reliability workflows",
        "difficulty": difficulty,
        "difficulty_profile": difficulty,
        "generator_seed": seed,
        "selected_option": {
            "focus": focus,
            "evaluation_axes": [focus, "operator reporting", "production-path correctness"],
        },
        "scenario_profile": {
            "entity_count": entity_count,
            "failure_modes": "basic" if difficulty == "junior" else "ambiguous" if difficulty == "staff" else "multi_step",
            "hidden_strictness": "basic" if difficulty == "junior" else "adversarial" if difficulty == "staff" else "production",
            "reporting_depth": "short" if difficulty == "junior" else "executive_plus_operator" if difficulty == "staff" else "operator",
        },
        "personalization": {
            "business_nouns": ["workspace", "incident", "customer"],
            "scenario_names": [f"{difficulty}-factory-scenario"],
            "fixture_field_names": ["workspace_id", "incident_id"],
            "hidden_test_emphasis": ["retry safety", "hardcoding resistance"],
        },
    }


def validate() -> None:
    manifest = load_manifest()
    contract = manifest.get("personalization_contract")
    if not contract:
        raise AssertionError("manifest missing personalization_contract")
    if contract.get("difficulty_levels") != ["junior", "senior", "staff"]:
        raise AssertionError("difficulty_levels must be junior, senior, staff")
    if not contract.get("allowed_focus_axes"):
        raise AssertionError("allowed_focus_axes must not be empty")

    original = CONTEXT.read_text() if CONTEXT.exists() else None
    snapshots: dict[str, bytes] = {}
    try:
        profiles = [
            profile_for("junior", contract["allowed_focus_axes"][0], 111, "low"),
            profile_for("senior", contract["allowed_focus_axes"][min(1, len(contract["allowed_focus_axes"]) - 1)], 222, "medium"),
            profile_for("staff", contract["allowed_focus_axes"][-1], 333, "high"),
        ]
        if manifest.get("template_slug") == "async-webhook-ledger":
            if CONTEXT.exists():
                CONTEXT.unlink()
            run_render()
            default_fixture = MAIN / "fixtures" / "public" / "public_events.jsonl"
            if not default_fixture.exists():
                raise AssertionError("async default render missing public fixture")
        for profile in profiles:
            write_context(profile)
            run_render()
            assert_candidate_safe(manifest)
            payload = assert_candidate_personalized(profile)
            assert_solution_cues(manifest, profile)
            snapshots[profile["difficulty"]] = json.dumps(payload, sort_keys=True).encode()
            if manifest.get("template_slug") == "payment-recovery-state-machine":
                fixture = MAIN / "fixtures" / "public" / "generated_payment_requests.jsonl"
                if not fixture.exists():
                    raise AssertionError("payment personalized render missing generated payment fixture")
                snapshots[profile["difficulty"] + "_fixture"] = fixture.read_bytes()
            if manifest.get("template_slug") == "workflow-recovery-reconciler":
                fixture = MAIN / "fixtures" / "public" / "generated_workflow_events.jsonl"
                if not fixture.exists():
                    raise AssertionError("workflow personalized render missing generated workflow fixture")
                rows = [json.loads(line) for line in fixture.read_text().splitlines() if line.strip()]
                if not rows:
                    raise AssertionError("workflow personalized fixture is empty")
                if not any(row.get("requires_reconciliation") for row in rows):
                    raise AssertionError("workflow personalized fixture does not include reconciliation cases")
                snapshots[profile["difficulty"] + "_fixture"] = fixture.read_bytes()
            if manifest.get("template_slug") == "async-webhook-ledger":
                fixture = MAIN / "fixtures" / "public" / "public_events.jsonl"
                if not fixture.exists():
                    raise AssertionError("async personalized render missing public fixture")
                snapshots[profile["difficulty"] + "_fixture"] = fixture.read_bytes()
        if snapshots["junior"] == snapshots["staff"]:
            raise AssertionError("personalization profile did not change between junior and staff")
        if manifest.get("template_slug") == "payment-recovery-state-machine" and snapshots["junior_fixture"] == snapshots["staff_fixture"]:
            raise AssertionError("payment fixture output did not change between junior and staff")
        if manifest.get("template_slug") == "workflow-recovery-reconciler" and snapshots["junior_fixture"] == snapshots["staff_fixture"]:
            raise AssertionError("workflow fixture output did not change between junior and staff")
        if manifest.get("template_slug") == "async-webhook-ledger" and snapshots["junior_fixture"] == snapshots["staff_fixture"]:
            raise AssertionError("async fixture output did not change between junior and staff")
    finally:
        if original is None:
            CONTEXT.unlink(missing_ok=True)
        else:
            CONTEXT.write_text(original)
    print("personalization validation passed")


if __name__ == "__main__":
    validate()
