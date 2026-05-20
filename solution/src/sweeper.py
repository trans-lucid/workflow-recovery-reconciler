from __future__ import annotations

from typing import Any


class WorkflowSweeper:
    def __init__(self, store: Any, recovery_queue: Any | None = None) -> None:
        self.store = store
        self.recovery_queue = recovery_queue

    def find_stale_workflows(self, *, older_than_seconds: int = 300) -> list[dict[str, Any]]:
        return self.store.list_stale(older_than_seconds=older_than_seconds, states={"started", "running"})

    def sweep_stale_workflows(self, *, older_than_seconds: int = 300) -> list[dict[str, Any]]:
        stale = self.find_stale_workflows(older_than_seconds=older_than_seconds)
        actions: list[dict[str, Any]] = []
        for workflow in stale:
            event_key = f"sweep-stale:{workflow['id']}"
            already_swept = any(event.get("event_key") == event_key for event in self.store.audit_events(workflow["id"]))
            updated = self.store.update_workflow(
                workflow["id"],
                state="needs_attention",
                last_error="stale lease requires external reconciliation",
                recommended_action="reconcile_external_truth",
            )
            self.store.append_audit(
                workflow["id"],
                event_key=event_key,
                event_type="stale_workflow_queued",
                details={"older_than_seconds": older_than_seconds},
            )
            if self.recovery_queue is not None and not already_swept:
                self.recovery_queue.send_recovery(
                    {
                        "workflow_id": workflow["id"],
                        "request_key": workflow["request_key"],
                        "reason": "stale_workflow",
                    }
                )
            actions.append(updated)
        return actions
