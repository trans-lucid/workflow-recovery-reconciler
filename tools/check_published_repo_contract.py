#!/usr/bin/env python3
"""Validate rendered branches before publishing a challenge repo.

This intentionally mirrors the backend repo tree checker, but runs locally
against generated/main and generated/solution before an agent pushes anything.
It catches branch-shape leaks, unresolved templates, broken TypeScript config,
and evaluator runners that would skip private tests.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    "",
    ".cfg",
    ".css",
    ".env",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsonl",
    ".jsx",
    ".md",
    ".mjs",
    ".py",
    ".rego",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"), "GitHub token"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key"),
    (re.compile(r"sk-[A-Za-z0-9]{24,}"), "OpenAI-style API key"),
    (re.compile(r"service_role", re.IGNORECASE), "Supabase service role marker"),
]


def resolve_path(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - actionable CLI error
        raise SystemExit(f"failed to read JSON {path}: {exc}") from exc


def rel_files(root: Path) -> list[str]:
    if not root.exists():
        return []
    paths: list[str] = []
    for path in root.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.is_file():
            paths.append(path.relative_to(root).as_posix())
    return sorted(paths)


def has_path(root: Path, rel: str) -> bool:
    return (root / rel).exists()


def has_dir(root: Path, rel: str) -> bool:
    return (root / rel).is_dir()


def has_any_file_under(root: Path, rel: str) -> bool:
    base = root / rel
    return base.is_dir() and any(p.is_file() for p in base.rglob("*"))


def read_text(path: Path) -> str | None:
    if not path.is_file():
        return None
    if path.suffix not in TEXT_SUFFIXES and path.name not in {"Makefile", "Dockerfile"}:
        return None
    try:
        if path.stat().st_size > 1_000_000:
            return None
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def parse_package(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def script_names(package: dict[str, Any]) -> set[str]:
    scripts = package.get("scripts")
    if not isinstance(scripts, dict):
        return set()
    return set(str(name) for name in scripts)


def script_body(package: dict[str, Any], name: str) -> str:
    scripts = package.get("scripts")
    if not isinstance(scripts, dict):
        return ""
    value = scripts.get(name)
    return value if isinstance(value, str) else ""


def forbidden_path_present(files: list[str], forbidden: str) -> str | None:
    needle = forbidden.rstrip("/")
    for rel in files:
        parts = rel.split("/")
        if rel == needle or rel.startswith(f"{needle}/") or needle in parts:
            return rel
    return None


def include_covers_src(include: Any) -> bool:
    if not isinstance(include, list):
        return False
    for item in include:
        raw = str(item).replace("\\", "/")
        if raw in {"**/*.ts", "**/*.tsx", "**/*", "."}:
            return True
        if raw.startswith("src/") or raw.startswith("./src/"):
            return True
    return False


def check_text_content(root: Path, branch: str, files: list[str], errors: list[str]) -> None:
    for rel in files:
        text = read_text(root / rel)
        if text is None:
            continue
        simulator_template = rel.startswith("simulators/wiremock/") or rel == "scripts/setup_gateway.py"
        if not simulator_template and ("{{" in text or "{%" in text):
            errors.append(f"{branch}: unresolved template syntax in {rel}")
        if "## Personalized Context" in text:
            errors.append(f"{branch}: raw personalized context leaked in {rel}")
        if "source_profile" in text or "source_profile_summary" in text:
            errors.append(f"{branch}: source profile marker leaked in {rel}")
        if "/Users/" in text or "Documents/GitHub" in text:
            errors.append(f"{branch}: local developer path leaked in {rel}")
        for pattern, label in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"{branch}: possible {label} in {rel}")


def check_candidate(candidate: Path, manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    files = rel_files(candidate)
    if not candidate.is_dir():
        return [f"candidate branch missing: {candidate}"]

    for required in ["README.md", "DEBRIEF.md", "Makefile"]:
        if required not in files:
            errors.append(f"candidate: missing required file {required}")
    if not has_dir(candidate, "src"):
        errors.append("candidate: missing src/ production code")
    if not has_any_file_under(candidate, "tests/public"):
        errors.append("candidate: missing public tests under tests/public/")
    if not any(has_any_file_under(candidate, rel) for rel in ["fixtures/public", "data", "tests/fixtures", "traces"]):
        errors.append("candidate: missing public fixture/data directory")
    if manifest.get("requires_docker_compose") and "docker-compose.yml" not in files:
        errors.append("candidate: manifest requires Docker Compose but docker-compose.yml is missing")
    if "package.json" not in files and "pyproject.toml" not in files:
        errors.append("candidate: missing package.json or pyproject.toml")

    forbidden = list(manifest.get("candidate_main_forbidden_paths") or [])
    forbidden.extend(
        [
            "generated/",
            "template_context.json",
            "__pycache__",
            ".pytest_cache",
            ".venv",
            "node_modules",
            ".env",
            ".env.local",
            ".DS_Store",
        ]
    )
    if not manifest.get("allow_candidate_generators", False):
        forbidden.append("generators/")
    for item in sorted(set(str(x) for x in forbidden)):
        found = forbidden_path_present(files, item)
        if found:
            errors.append(f"candidate: forbidden path found: {found}")

    check_text_content(candidate, "candidate", files, errors)

    for rel in ["README.md", "DEBRIEF.md"]:
        text = read_text(candidate / rel) or ""
        lowered = text.lower()
        if "hidden test" in lowered or "private evaluator" in lowered or "solution branch" in lowered:
            errors.append(f"candidate: private evaluation language leaked in {rel}")

    for rel in ["Makefile", "package.json"]:
        text = read_text(candidate / rel) or ""
        if "../generators" in text or " ../" in text and "seed" in text:
            errors.append(f"candidate: {rel} references template-parent paths")

    package = parse_package(candidate / "package.json")
    if package:
        scripts = package.get("scripts", {})
        if isinstance(scripts, dict) and any("tsc" in str(body) for body in scripts.values()):
            if "tsconfig.json" not in files:
                errors.append("candidate: package scripts run tsc but tsconfig.json is missing")
            else:
                tsconfig = load_json(candidate / "tsconfig.json")
                include = tsconfig.get("include")
                if has_dir(candidate, "src") and not include_covers_src(include):
                    errors.append("candidate: tsconfig include does not cover root src/")
                for item in include or []:
                    raw = str(item).replace("\\", "/")
                    if raw.startswith("candidate/"):
                        errors.append("candidate: tsconfig includes template-only candidate/ path")
                    if raw.startswith("solution/") or raw.startswith("evaluator/"):
                        errors.append("candidate: tsconfig includes private solution/evaluator paths")
        bad_scripts = []
        for name, body in (scripts or {}).items() if isinstance(scripts, dict) else []:
            body_text = str(body)
            if "solution/" in body_text or "evaluator/" in body_text or "tests_hidden" in body_text:
                bad_scripts.append(str(name))
        if bad_scripts:
            errors.append(f"candidate: package scripts expose private paths: {', '.join(sorted(bad_scripts))}")

    result_files = [rel for rel in files if rel.startswith("results/") and rel != "results/.gitkeep"]
    if result_files:
        errors.append(f"candidate: results directory contains generated outputs: {', '.join(result_files[:5])}")

    return errors


def check_solution(solution: Path, manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    files = rel_files(solution)
    if not solution.is_dir():
        return [f"solution branch missing: {solution}"]

    for required in ["README.md", "DEBRIEF.md", "SOLUTION.md"]:
        if required not in files:
            errors.append(f"solution: missing required file {required}")
    for required_dir in ["src", "tests/public", "solution", "evaluator"]:
        if not has_dir(solution, required_dir):
            errors.append(f"solution: missing required directory {required_dir}/")
    if not has_path(solution, "evaluator/run_hidden.sh"):
        errors.append("solution: missing evaluator/run_hidden.sh")
    if not any(has_any_file_under(solution, rel) for rel in ["evaluator/tests_hidden", "tests_hidden"]):
        errors.append("solution: hidden tests are missing")

    forbidden = ["generated/", "__pycache__", ".pytest_cache", ".venv", "node_modules", ".env", ".DS_Store"]
    for item in forbidden:
        found = forbidden_path_present(files, item)
        if found:
            errors.append(f"solution: forbidden transient path found: {found}")

    check_text_content(solution, "solution", files, errors)

    run_public = read_text(solution / "evaluator/run_public.sh") or ""
    if run_public:
        if "candidate" in run_public and not has_dir(solution, "candidate"):
            errors.append("solution: evaluator/run_public.sh references candidate/ but generated solution has no candidate/ directory")

    run_hidden = read_text(solution / "evaluator/run_hidden.sh") or ""
    if run_hidden:
        if "candidate" in run_hidden and not has_dir(solution, "candidate"):
            errors.append("solution: evaluator/run_hidden.sh references candidate/ but generated solution has no candidate/ directory")
        if "tests_hidden" not in run_hidden and "test:solution" not in run_hidden and "validate:solution" not in run_hidden:
            errors.append("solution: evaluator/run_hidden.sh does not appear to execute hidden tests")
        for script in re.findall(r"npm\s+run\s+([A-Za-z0-9:_-]+)", run_hidden):
            if script not in script_names(parse_package(solution / "package.json")):
                errors.append(f"solution: evaluator/run_hidden.sh calls missing npm script {script}")

    package = parse_package(solution / "package.json")
    if package:
        scripts = package.get("scripts", {})
        if isinstance(scripts, dict) and any("tsc" in str(body) for body in scripts.values()):
            if "tsconfig.json" not in files:
                errors.append("solution: package scripts run tsc but tsconfig.json is missing")
            else:
                tsconfig = load_json(solution / "tsconfig.json")
                if has_dir(solution, "src") and not include_covers_src(tsconfig.get("include")):
                    errors.append("solution: tsconfig include does not cover root src/")
        test_solution = script_body(package, "test:solution")
        if test_solution and "tests_hidden" not in test_solution and "evaluator/" not in test_solution:
            errors.append("solution: test:solution script does not include evaluator hidden tests")

    solution_text = "\n".join(
        text
        for text in [
            read_text(solution / "SOLUTION.md") or "",
            read_text(solution / "PERSONALIZATION.md") or "",
        ]
        if text
    )
    lowered = solution_text.lower()
    cue_terms = [
        "focus",
        "difficulty",
        "hidden test",
        "rubric",
        "debrief",
        "expected failure",
    ]
    missing = [term for term in cue_terms if term not in lowered]
    if missing:
        errors.append(f"solution: SOLUTION.md missing private cue terms: {', '.join(missing)}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-dir", default="generated/main")
    parser.add_argument("--solution-dir", default="generated/solution")
    parser.add_argument("--manifest", default="translucid-template.json")
    parser.add_argument("--json", action="store_true", help="emit machine-readable result")
    args = parser.parse_args()

    manifest_path = resolve_path(args.manifest)
    manifest = load_json(manifest_path)
    candidate = resolve_path(args.candidate_dir)
    solution = resolve_path(args.solution_dir)

    candidate_errors = check_candidate(candidate, manifest)
    solution_errors = check_solution(solution, manifest)
    errors = candidate_errors + solution_errors
    result = {
        "status": "passed" if not errors else "failed",
        "candidate_dir": candidate.relative_to(ROOT).as_posix() if candidate.is_relative_to(ROOT) else str(candidate),
        "solution_dir": solution.relative_to(ROOT).as_posix() if solution.is_relative_to(ROOT) else str(solution),
        "errors": errors,
    }
    if args.json:
        print(json.dumps(result, indent=2))
    elif errors:
        print("published repo contract failed:")
        for error in errors:
            print(f"- {error}")
    else:
        print("published repo contract passed")
        print(f"- candidate: {result['candidate_dir']}")
        print(f"- solution: {result['solution_dir']}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
