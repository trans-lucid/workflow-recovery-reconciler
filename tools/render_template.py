#!/usr/bin/env python3
"""Render candidate-safe and private solution previews for this template."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "generated"
MAIN = GENERATED / "main"
SOLUTION = GENERATED / "solution"
TEMPLATE_TITLE = "Workflow Recovery Reconciler"
PROFILE_ARTIFACT = Path("fixtures/public/generated_workflow_events.jsonl")


def load_manifest() -> dict:
    path = ROOT / "translucid-template.json"
    return json.loads(path.read_text()) if path.exists() else {}


def load_template_context() -> dict:
    path = ROOT / "template_context.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _safe_scalar(value: object, limit: int = 500) -> str:
    text = str(value).replace("\r", " ").strip()
    text = re.sub(r"(?:/[^\s]+){2,}", "[redacted-path]", text)
    text = re.sub(r"(?i)(sk-[a-z0-9_-]{8,}|ghp_[a-z0-9_]{8,}|AKIA[0-9A-Z]{12,})", "[redacted-secret]", text)
    return text[:limit]


def _safe_list(values: object, limit: int = 8) -> list[str]:
    if not isinstance(values, list):
        return []
    return [_safe_scalar(value, 120) for value in values[:limit] if str(value).strip()]


def selected_option(context: dict) -> dict:
    value = context.get("selected_option")
    return value if isinstance(value, dict) else {}


def personalization(context: dict) -> dict:
    value = context.get("personalization")
    return value if isinstance(value, dict) else {}


def scenario_profile(context: dict) -> dict:
    value = context.get("scenario_profile")
    return value if isinstance(value, dict) else {}


def difficulty(context: dict) -> str:
    raw = _safe_scalar(context.get("difficulty") or context.get("difficulty_profile") or "senior", 40).lower()
    return raw if raw in {"junior", "senior", "staff"} else "senior"


def focus(context: dict) -> str:
    selected = selected_option(context)
    return _safe_scalar(selected.get("focus") or context.get("focus") or "workflow recovery correctness", 160)


def evaluation_axes(context: dict) -> list[str]:
    selected = selected_option(context)
    axes = _safe_list(selected.get("evaluation_axes"))
    if axes:
        return axes
    manifest_axes = load_manifest().get("personalization_contract", {}).get("allowed_focus_axes", [])
    return _safe_list(manifest_axes, 4)


def scenario_summary(context: dict) -> str:
    if context.get("theme"):
        return _safe_scalar(context["theme"], 300)
    nouns = _safe_list(personalization(context).get("business_nouns"), 4)
    if nouns:
        return f"Recover stale and ambiguous {', '.join(nouns)} workflows with the selected reliability focus."
    return f"Repair the {TEMPLATE_TITLE} production path for a realistic SaaS control-plane scenario."


def safe_business_terms(context: dict) -> list[str]:
    terms: list[str] = []
    p = personalization(context)
    for key in ("business_nouns", "scenario_names", "fixture_field_names"):
        terms.extend(_safe_list(p.get(key), 6))
    return terms[:12]


def candidate_scenario_block(context: dict) -> str:
    if not context:
        return ""
    lines = ["", "## Scenario Variant"]
    title = _safe_scalar(context.get("challenge_title") or TEMPLATE_TITLE, 160)
    lines.append(f"- Challenge: {title}")
    if context.get("company_name"):
        lines.append(f"- Company context: {_safe_scalar(context['company_name'], 120)}")
    if context.get("role"):
        lines.append(f"- Role: {_safe_scalar(context['role'], 120)}")
    if context.get("time_limit"):
        lines.append(f"- Time limit: {_safe_scalar(context['time_limit'], 80)}")
    lines.append(f"- Difficulty: {difficulty(context)}")
    lines.append(f"- Focus: {focus(context)}")
    axes = evaluation_axes(context)
    if axes:
        lines.append("- Evaluation axes: " + ", ".join(axes))
    lines.append(f"- Scenario: {scenario_summary(context)}")
    terms = safe_business_terms(context)
    if terms:
        lines.append("- Domain terms: " + ", ".join(terms))
    lines.append("")
    return "\n".join(lines)


def profile_payload(context: dict) -> dict:
    p = personalization(context)
    return {
        "schema_version": "1.0",
        "template_slug": load_manifest().get("template_slug"),
        "difficulty": difficulty(context),
        "focus": focus(context),
        "evaluation_axes": evaluation_axes(context),
        "generator_seed": int(context.get("generator_seed") or 20260520),
        "scenario_profile": scenario_profile(context),
        "scenario_knobs": {
            "entity_count": scenario_profile(context).get("entity_count", "medium"),
            "failure_modes": scenario_profile(context).get("failure_modes", "multi_step"),
            "hidden_strictness": scenario_profile(context).get("hidden_strictness", "production"),
            "reporting_depth": scenario_profile(context).get("reporting_depth", "operator"),
        },
        "personalization": {
            "business_nouns": _safe_list(p.get("business_nouns"), 8),
            "scenario_names": _safe_list(p.get("scenario_names"), 8),
            "fixture_field_names": _safe_list(p.get("fixture_field_names"), 8),
        },
    }


def render_candidate_text(template: str, context: dict) -> str:
    rendered = template
    selected = selected_option(context)
    replacements = {
        "company_name": context.get("company_name", ""),
        "company_context": context.get("company_description") or context.get("company_name", ""),
        "challenge_title": context.get("challenge_title", ""),
        "role": context.get("role", ""),
        "theme": context.get("theme", ""),
        "time_limit": context.get("time_limit", ""),
        "company_description": context.get("company_description", ""),
        "difficulty": difficulty(context),
        "difficulty_profile": difficulty(context),
        "selected_option.focus": selected.get("focus", ""),
        "selected_option.evaluation_axes": ", ".join(evaluation_axes(context)),
    }
    for key, value in replacements.items():
        replacement = _safe_scalar(value)
        rendered = rendered.replace("{{ " + key + " }}", replacement)
        rendered = rendered.replace("{{" + key + "}}", replacement)
        rendered = re.sub(
            r"{{\s*" + re.escape(key) + r"\s*\|\s*default\((['\"])(.*?)\1\)\s*}}",
            lambda match, replacement=replacement: replacement or match.group(2),
            rendered,
        )
    block = candidate_scenario_block(context)
    return rendered.rstrip() + ("\n" + block if block else "") + "\n"


def apply_template_context(rendered_root: Path) -> None:
    context = load_template_context()
    for name in ("README.md", "DEBRIEF.md"):
        source = ROOT / f"{name}.j2"
        target = rendered_root / name
        if source.exists():
            target.write_text(render_candidate_text(source.read_text(), context))
    if context:
        artifact = rendered_root / "fixtures" / "public" / "personalization_profile.json"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(json.dumps(profile_payload(context), indent=2, sort_keys=True) + "\n")


def write_solution_personalization(solution_root: Path) -> None:
    context = load_template_context()
    manifest = load_manifest()
    profile = profile_payload(context)
    expected = manifest.get("expected_failure_markers", [])
    lines = [
        "# Private Personalization Notes",
        "",
        "## Focus Being Evaluated",
        f"Difficulty: {profile['difficulty']}",
        f"Focus: {profile['focus']}",
        "Evaluation axes: " + ", ".join(profile["evaluation_axes"]),
        "",
        "## Scenario Personalization",
        f"Scenario: {scenario_summary(context)}",
        "Business nouns: " + ", ".join(profile["personalization"]["business_nouns"]),
        "Scenario names: " + ", ".join(profile["personalization"]["scenario_names"]),
        "Fixture field names: " + ", ".join(profile["personalization"]["fixture_field_names"]),
        "Hidden test emphasis: " + ", ".join(_safe_list(personalization(context).get("hidden_test_emphasis"), 8)),
        "",
        "## Expected Failure Classes",
        ", ".join(expected),
        "",
        "## Public Test Purpose",
        "Public tests verify the candidate-facing workflow recovery contract and expected starter failure markers.",
        "",
        "## Hidden Test Intent",
        "Hidden tests exercise stricter external-truth, stale-sweeper, attempt-history, non-retryable, duplicate-run, and report-evidence cases.",
        "",
        "## Scoring Rubric",
        "Score against the selected focus, state recovery correctness, retry safety, external truth handling, report quality, and debrief reasoning.",
        "",
        "## Debrief Answer Cues",
        "Strong answers should explain idempotency boundaries, stale-state repair, external truth precedence, attempt history, and operator next actions.",
        "",
        "## Validation Commands And Expected Behavior",
        "- make validate-solution: passes for the reference solution.",
        "- make validate-candidate-main-expected-failure: passes by confirming the starter fails for expected markers.",
        "- make validate-docker-integration: passes by confirming the Docker-backed expected failure and solution path.",
        "- make validate-personalization: passes only when rendered artifacts reflect the selected difficulty and focus safely.",
        "",
    ]
    (solution_root / "PERSONALIZATION.md").write_text("\n".join(lines))


def copytree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".venv", "*.egg-info", "results", ".DS_Store")
    shutil.copytree(src, dst, ignore=ignore)


def ensure_results_dir(rendered_root: Path) -> None:
    results = rendered_root / "results"
    results.mkdir(exist_ok=True)
    (results / ".gitkeep").write_text("")


def run_profile_generator(rendered_root: Path) -> None:
    context_path = ROOT / "template_context.json"
    if not context_path.exists():
        return
    generator = ROOT / "generators" / "generate_fixture.py"
    out = rendered_root / PROFILE_ARTIFACT
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(generator), "--profile", str(context_path), "--out", str(out)], cwd=ROOT, check=True)


def render_main() -> Path:
    copytree(ROOT / "candidate", MAIN)
    ensure_results_dir(MAIN)
    apply_template_context(MAIN)
    run_profile_generator(MAIN)
    return MAIN


def render_solution() -> Path:
    copytree(ROOT / "candidate", SOLUTION)
    ensure_results_dir(SOLUTION)
    apply_template_context(SOLUTION)
    run_profile_generator(SOLUTION)
    shutil.copytree(ROOT / "solution", SOLUTION / "solution", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", "*.egg-info", ".DS_Store"))
    shutil.copytree(ROOT / "evaluator", SOLUTION / "evaluator", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", "*.egg-info", ".DS_Store"))
    (SOLUTION / "SOLUTION.md").write_text(render_candidate_text((ROOT / "solution" / "SOLUTION.md.j2").read_text(), load_template_context()))
    shutil.copy2(ROOT / "evaluator" / "rubric.md", SOLUTION / "rubric.md")
    write_solution_personalization(SOLUTION)
    return SOLUTION


def main() -> None:
    if GENERATED.exists():
        shutil.rmtree(GENERATED)
    GENERATED.mkdir(parents=True)
    main_dir = render_main()
    solution_dir = render_solution()
    print(f"rendered candidate main: {main_dir}")
    print(f"rendered solution: {solution_dir}")


if __name__ == "__main__":
    main()
