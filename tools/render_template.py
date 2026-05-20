#!/usr/bin/env python3
"""Render candidate-safe and private solution previews for this template."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "generated"
MAIN = GENERATED / "main"
SOLUTION = GENERATED / "solution"


def load_template_context() -> dict:
    path = ROOT / "template_context.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _safe_scalar(value: object) -> str:
    text = str(value).replace("\r", " ").strip()
    text = re.sub(r"(?:/[^\s]+){2,}", "[redacted-path]", text)
    return text[:500]


def _safe_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [_safe_scalar(value) for value in values[:8]]


def context_block(context: dict) -> str:
    if not context:
        return ""
    lines = ["", "## Personalized Context"]
    mapping = [
        ("challenge_title", "Challenge title"),
        ("company_name", "Company"),
        ("role", "Role"),
        ("time_limit", "Time limit"),
        ("theme", "Scenario"),
        ("company_description", "Company context"),
    ]
    for key, label in mapping:
        if context.get(key):
            lines.append(f"- **{label}:** {_safe_scalar(context[key])}")
    selected = context.get("selected_option") if isinstance(context.get("selected_option"), dict) else {}
    if selected.get("focus"):
        lines.append(f"- **Focus:** {_safe_scalar(selected['focus'])}")
    axes = _safe_list(selected.get("evaluation_axes"))
    if axes:
        lines.append("- **Evaluation axes:** " + ", ".join(axes))
    profile = context.get("source_profile_summary") if isinstance(context.get("source_profile_summary"), dict) else {}
    signals = _safe_list(profile.get("architecture_signals"))
    if signals:
        lines.append("- **Architecture signals:** " + ", ".join(signals))
    stack = _safe_list(profile.get("stack"))
    if stack:
        lines.append("- **Stack:** " + ", ".join(stack))
    lines.append("")
    return "\n".join(lines)


def render_candidate_text(template: str, context: dict) -> str:
    rendered = template
    replacements = {
        "company_name": context.get("company_name", ""),
        "challenge_title": context.get("challenge_title", ""),
        "role": context.get("role", ""),
        "theme": context.get("theme", ""),
        "time_limit": context.get("time_limit", ""),
        "company_description": context.get("company_description", ""),
    }
    selected = context.get("selected_option") if isinstance(context.get("selected_option"), dict) else {}
    replacements["selected_option.focus"] = selected.get("focus", "")
    replacements["selected_option.evaluation_axes"] = ", ".join(_safe_list(selected.get("evaluation_axes")))
    for key, value in replacements.items():
        rendered = rendered.replace("{{ " + key + " }}", _safe_scalar(value))
        rendered = rendered.replace("{{" + key + "}}", _safe_scalar(value))
    block = context_block(context)
    return rendered.rstrip() + ("\n" + block if block else "") + "\n"


def apply_template_context(rendered_root: Path) -> None:
    context = load_template_context()
    for name in ("README.md", "DEBRIEF.md"):
        source = ROOT / f"{name}.j2"
        target = rendered_root / name
        if source.exists():
            target.write_text(render_candidate_text(source.read_text(), context))


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
    apply_template_context(MAIN)
    

    copytree(ROOT / "candidate", SOLUTION)
    apply_template_context(SOLUTION)
    shutil.copytree(ROOT / "solution", SOLUTION / "solution", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(ROOT / "evaluator", SOLUTION / "evaluator", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (SOLUTION / "SOLUTION.md").write_text((ROOT / "solution" / "SOLUTION.md.j2").read_text())
    (SOLUTION / "rubric.md").write_text((ROOT / "evaluator" / "rubric.md").read_text())

    print(f"rendered candidate main preview: {MAIN}")
    print(f"rendered private solution preview: {SOLUTION}")


if __name__ == "__main__":
    main()
