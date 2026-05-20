#!/usr/bin/env python3
"""Safety checks for rendered candidate main."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "generated" / "main"
SECRET_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"SUPABASE_SERVICE_ROLE_KEY", re.IGNORECASE),
    re.compile(r"PINECONE_API_KEY", re.IGNORECASE),
    re.compile(r"OPENAI_API_KEY", re.IGNORECASE),
]
FORBIDDEN_MAIN_PARTS = {
    "solution",
    "evaluator",
    "tests_hidden",
    "fixtures_hidden",
    "SOLUTION.md",
    "SOLUTION.md.j2",
    "rubric.md",
    "expected",
    "source-dossiers",
    "template.yaml",
}
FORBIDDEN_TEXT = [
    "/Users/",
    "customer source",
    "real customer",
]


def fail(message: str) -> None:
    print(f"safety scan failed: {message}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    if not MAIN.exists():
        fail("generated/main does not exist; run make render first")

    for path in MAIN.rglob("*"):
        relative = path.relative_to(MAIN)
        if set(relative.parts) & FORBIDDEN_MAIN_PARTS:
            fail(f"candidate main leaked private material at {relative}")
        if path.is_file() and path.stat().st_size < 2_000_000:
            text = path.read_text(errors="ignore")
            for pattern in SECRET_PATTERNS:
                if pattern.search(text):
                    fail(f"possible secret in {path.relative_to(ROOT)}")
            for forbidden in FORBIDDEN_TEXT:
                if forbidden in text:
                    fail(f"forbidden source/customer marker in {path.relative_to(ROOT)}")

    print("safety scan passed")


if __name__ == "__main__":
    main()

