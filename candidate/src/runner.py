from __future__ import annotations

from datetime import timedelta
from typing import Any

from src.external_client import ExternalNonRetryable, ExternalTimeout
from src.workflow_store import utcnow


REQUIRED_FIELDS = {"request_key", "workflow_type", "resource_id"}


class WorkflowRunner:
    def __init__(self, store: Any, external_client: Any) -> None:
        self.store = store
        self.external_client = external_client

    def start_workflow(self, request: dict[str, Any]) -> dict[str, Any]:
        missing = sorted(REQUIRED_FIELDS - set(request))
        if missing:
            raise ValueError(f"missing required fields: {', '.join(missing)}")

        # Starter bug: this ignores request_key idempotency and calls the
        # external service again on every retry.
        workflow = self.store.create_workflow(
            {
                "request_key": request["request_key"],
                "workflow_type": request["workflow_type"],
                "resource_id": request["resource_id"],
                "state": "started",
                "lease_expires_at": utcnow() + timedelta(minutes=5),
            }
        )
        self.store.append_audit(workflow["id"], event_type="workflow_created", details={"request_key": request["request_key"]})

        try:
            external = self.external_client.start_workflow(request)
        except ExternalTimeout as exc:
            # Starter bug: a timeout is ambiguous. This marks the workflow as
            # failed without recording an attempt or reconciling external truth.
            return self.store.update_workflow(
                workflow["id"],
                state="failed",
                last_error=str(exc),
                recommended_action="tell_user_to_retry",
            )
        except ExternalNonRetryable as exc:
            self.store.add_attempt(workflow["id"], action="external_start", status="non_retryable", error=str(exc))
            return self.store.update_workflow(
                workflow["id"],
                state="failed",
                last_error=str(exc),
                recommended_action="manual_review",
            )

        self.store.add_attempt(
            workflow["id"],
            action="external_start",
            status="accepted",
            external_job_id=external.get("external_job_id"),
            evidence=external,
        )
        return self.store.update_workflow(
            workflow["id"],
            state="running",
            external_job_id=external.get("external_job_id"),
            last_external_state=external.get("state"),
            recommended_action="watch",
        )

