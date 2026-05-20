#!/usr/bin/env python3
"""Validate rendered candidate and private solution layout."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "generated"
MAIN = GENERATED / "main"
SOLUTION = GENERATED / "solution"


FORBIDDEN_MAIN_PARTS = {
    "solution",
    "evaluator",
    "tests_hidden",
    "fixtures_hidden",
    "SOLUTION.md",
    "SOLUTION.md.j2",
    "rubric.md",
    "source-dossiers",
    "template.yaml",
    "metadata",
}


def fail(message: str) -> None:
    print(f"render contract failed: {message}", file=sys.stderr)
    sys.exit(1)


def contains_public_tests(root: Path) -> bool:
    tests_dir = root / "tests"
    if tests_dir.exists() and any(path.is_file() for path in tests_dir.rglob("*")):
        return True
    nested = root / "candidate" / "tests"
    return nested.exists() and any(path.is_file() for path in nested.rglob("*"))


def main() -> None:
    if not MAIN.exists():
        fail("generated/main does not exist")
    if not SOLUTION.exists():
        fail("generated/solution does not exist")
    if not (MAIN / "README.md").exists():
        fail("generated/main/README.md does not exist")
    if not (MAIN / "DEBRIEF.md").exists():
        fail("generated/main/DEBRIEF.md does not exist")
    if not contains_public_tests(MAIN):
        fail("generated/main has no public tests")

    for path in MAIN.rglob("*"):
        rel = path.relative_to(MAIN)
        if set(rel.parts) & FORBIDDEN_MAIN_PARTS:
            fail(f"forbidden candidate-main path found: generated/main/{rel}")

    solution_has_solution = (SOLUTION / "solution").exists() or (SOLUTION / "SOLUTION.md").exists()
    if not solution_has_solution:
        fail("generated/solution does not contain solution material")
    solution_has_evaluator = (SOLUTION / "evaluator").exists() or any("tests_hidden" in path.parts for path in SOLUTION.rglob("*"))
    if not solution_has_evaluator:
        fail("generated/solution does not contain evaluator or hidden tests")

    print("render contract passed")


if __name__ == "__main__":
    main()
