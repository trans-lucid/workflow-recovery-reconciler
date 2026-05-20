#!/usr/bin/env python3
"""Lightweight safety checks for rendered candidate main."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "generated" / "main"
if not MAIN.is_absolute():
    MAIN = ROOT / MAIN
MANIFEST = ROOT / "translucid-template.json"

DEFAULT_FORBIDDEN = [
    "solution/",
    "evaluator/",
    "tests_hidden/",
    "fixtures_hidden/",
    "SOLUTION.md",
    "SOLUTION.md.j2",
    "rubric.md",
    "source-dossiers/",
    "template.yaml",
    "metadata/",
]

SECRET_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"OPENAI_API_KEY\s*="),
    re.compile(r"PINECONE_API_KEY\s*="),
    re.compile(r"SUPABASE_SERVICE_ROLE_KEY\s*="),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"customer[_-]?source", re.IGNORECASE),
    re.compile(r"real[_-]?customer[_-]?data", re.IGNORECASE),
]


def fail(messages: list[str]) -> None:
    print("safety scan failed:", file=sys.stderr)
    for message in messages:
        print(f"- {message}", file=sys.stderr)
    sys.exit(1)


def forbidden_paths() -> list[str]:
    if MANIFEST.exists():
        data = json.loads(MANIFEST.read_text())
        configured = data.get("candidate_main_forbidden_paths")
        if isinstance(configured, list) and configured:
            return [str(item) for item in configured]
    return DEFAULT_FORBIDDEN


def is_forbidden(rel: Path, rule: str) -> bool:
    normalized = rel.as_posix()
    stripped = rule.rstrip("/")
    if rule.endswith("/"):
        return normalized == stripped or normalized.startswith(stripped + "/")
    return rel.name == rule or normalized == rule


def main() -> None:
    errors: list[str] = []
    if not MAIN.exists():
        fail([f"generated candidate directory missing: {MAIN}"])

    rules = forbidden_paths()
    for path in MAIN.rglob("*"):
        rel = path.relative_to(MAIN)
        for rule in rules:
            if is_forbidden(rel, rule):
                errors.append(f"forbidden path found: {MAIN.name}/{rel}")
        if path.is_file() and path.stat().st_size < 2_000_000:
            text = path.read_text(errors="ignore")
            for pattern in SECRET_PATTERNS:
                if pattern.search(text):
                    errors.append(f"possible secret or private marker in {path.relative_to(ROOT)}")

    if errors:
        fail(errors)
    print("safety scan passed")


if __name__ == "__main__":
    main()
