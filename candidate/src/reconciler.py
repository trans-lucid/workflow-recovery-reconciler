from __future__ import annotations

from typing import Any


class WorkflowReconciler:
    def __init__(self, store: Any, external_client: Any, recovery_queue: Any | None = None) -> None:
        self.store = store
        self.external_client = external_client
        self.recovery_queue = recovery_queue

    def reconcile_workflow(self, workflow_id: str) -> dict[str, Any]:
        workflow = self.store.find_by_id(workflow_id)
        if workflow is None:
            raise KeyError(f"unknown workflow {workflow_id}")

        # Starter bug: local state wins even when external truth proves the
        # workflow completed, disappeared, or needs attention.
        if workflow["state"] in {"running", "complete", "failed"}:
            self.store.append_audit(
                workflow_id,
                event_type="reconcile_skipped_local_truth",
                details={"state": workflow["state"]},
            )
            return workflow

        external = self.external_client.get_workflow_status(workflow["request_key"], workflow.get("external_job_id"))
        self.store.add_attempt(
            workflow_id,
            action="external_status",
            status=external.get("state", "unknown"),
            external_job_id=external.get("external_job_id"),
            evidence=external,
        )
        return self.store.update_workflow(
            workflow_id,
            last_external_state=external.get("state"),
            recommended_action="manual_review",
        )

    def drain_recovery_queue(self, limit: int = 10) -> list[dict[str, Any]]:
        if self.recovery_queue is None:
            return []
        results = []
        for message in self.recovery_queue.receive(max_messages=limit):
            workflow_id = message["workflow_id"]
            results.append(self.reconcile_workflow(workflow_id))
            self.recovery_queue.delete(message)
        return results

