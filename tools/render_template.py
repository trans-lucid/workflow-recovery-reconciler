#!/usr/bin/env python3
"""Render candidate-safe and private solution previews for this template."""

from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "generated"
MAIN = GENERATED / "main"
SOLUTION = GENERATED / "solution"


def copytree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(
        src,
        dst,
        ignore=shutil.ignore_patterns(
            ".pytest_cache",
            "__pycache__",
            "*.pyc",
            ".venv",
            "*.egg-info",
            "results",
        ),
    )


def main() -> None:
    if GENERATED.exists():
        shutil.rmtree(GENERATED)
    GENERATED.mkdir()

    copytree(ROOT / "candidate", MAIN)
    (MAIN / "results").mkdir(exist_ok=True)
    (MAIN / "results" / ".gitkeep").write_text("")
    (MAIN / "README.md").write_text((ROOT / "README.md.j2").read_text())
    (MAIN / "DEBRIEF.md").write_text((ROOT / "DEBRIEF.md.j2").read_text())

    copytree(ROOT / "candidate", SOLUTION)
    shutil.copytree(ROOT / "solution", SOLUTION / "solution", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(ROOT / "evaluator", SOLUTION / "evaluator", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (SOLUTION / "SOLUTION.md").write_text((ROOT / "solution" / "SOLUTION.md.j2").read_text())
    (SOLUTION / "rubric.md").write_text((ROOT / "evaluator" / "rubric.md").read_text())

    print(f"rendered candidate main preview: {MAIN}")
    print(f"rendered private solution preview: {SOLUTION}")


if __name__ == "__main__":
    main()
