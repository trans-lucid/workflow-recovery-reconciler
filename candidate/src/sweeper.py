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
            # Starter bug: stale means "unknown" until the external system is
            # queried. Marking every stale workflow failed can strand completed
            # external jobs and create unsafe retries.
            updated = self.store.update_workflow(
                workflow["id"],
                state="failed",
                last_error="stale lease expired",
                recommended_action="restart_from_scratch",
            )
            self.store.append_audit(
                workflow["id"],
                event_type="stale_workflow_failed",
                details={"older_than_seconds": older_than_seconds},
            )
            actions.append(updated)
        return actions

