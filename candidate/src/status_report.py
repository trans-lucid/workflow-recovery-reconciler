from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from src.workflow_store import serialize_record


def build_status_report(store: Any) -> dict[str, Any]:
    workflows = [serialize_record(record) for record in store.list_workflows()]
    by_state = Counter(record["state"] for record in workflows)
    items = []
    for workflow in workflows:
        attempts = [serialize_record(record) for record in store.attempts_for_workflow(workflow["id"])]
        audit = [serialize_record(record) for record in store.audit_events(workflow["id"])]
        items.append(
            {
                "workflow_id": workflow["id"],
                "request_key": workflow["request_key"],
                "state": workflow["state"],
                "external_job_id": workflow.get("external_job_id"),
                # Starter bug: the report exposes local state but does not
                # summarize external evidence or a reliable next action.
                "attempts": attempts,
                "audit_events": audit,
                "recommended_action": workflow.get("recommended_action") or "inspect",
            }
        )
    return {
        "schema_version": "workflow-recovery-report/v1",
        "summary": {"total_workflows": len(workflows), "by_state": dict(by_state)},
        "workflows": items,
    }


def write_status_report(store: Any, output_path: str | Path) -> dict[str, Any]:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    report = build_status_report(store)
    path.write_text(json.dumps(report, indent=2, sort_keys=True))
    summary_path = path.parent / "summary.md"
    summary_path.write_text(
        "\n".join(
            [
                "# Workflow Recovery Summary",
                "",
                f"Total workflows: {report['summary']['total_workflows']}",
                f"By state: {report['summary']['by_state']}",
                "",
            ]
        )
    )
    return report

