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

        external = self.external_client.get_workflow_status(workflow["request_key"], workflow.get("external_job_id"))
        external_state = external.get("state", "unknown")
        attempt_exists = any(
            attempt.get("action") == "external_status"
            and attempt.get("status") == external_state
            and attempt.get("external_job_id") == external.get("external_job_id")
            for attempt in self.store.attempts_for_workflow(workflow_id)
        )
        if not attempt_exists:
            self.store.add_attempt(
                workflow_id,
                action="external_status",
                status=external_state,
                external_job_id=external.get("external_job_id"),
                evidence=external,
            )
        self.store.append_audit(
            workflow_id,
            event_key=f"reconcile:{workflow_id}:{external_state}",
            event_type="external_truth_checked",
            details=external,
        )

        if external_state in {"completed", "complete", "settled"}:
            return self.store.update_workflow(
                workflow_id,
                state="complete",
                external_job_id=external.get("external_job_id") or workflow.get("external_job_id"),
                last_external_state=external_state,
                last_error=None,
                recommended_action="none",
            )

        if external_state in {"running", "pending", "started"}:
            return self.store.update_workflow(
                workflow_id,
                state="running",
                external_job_id=external.get("external_job_id") or workflow.get("external_job_id"),
                last_external_state=external_state,
                recommended_action="watch",
            )

        if external_state in {"non_retryable", "invalid", "failed_permanent"}:
            return self.store.update_workflow(
                workflow_id,
                state="needs_attention",
                last_external_state=external_state,
                last_error="external reported non-retryable failure",
                recommended_action="fix_request_before_retry",
            )

        return self.store.update_workflow(
            workflow_id,
            state="needs_attention",
            last_external_state=external_state,
            last_error="external truth unknown",
            recommended_action="check_external_truth",
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
