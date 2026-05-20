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

        existing = self.store.find_by_request_key(request["request_key"])
        if existing is not None:
            self.store.append_audit(
                existing["id"],
                event_type="workflow_start_reused",
                event_key=f"reuse:{request['request_key']}",
                details={"request_key": request["request_key"]},
            )
            return existing

        workflow = self.store.create_workflow(
            {
                "request_key": request["request_key"],
                "workflow_type": request["workflow_type"],
                "resource_id": request["resource_id"],
                "state": "started",
                "lease_expires_at": utcnow() + timedelta(minutes=5),
            }
        )
        self.store.append_audit(
            workflow["id"],
            event_type="workflow_created",
            event_key=f"create:{request['request_key']}",
            details={"request_key": request["request_key"]},
        )

        try:
            external = self.external_client.start_workflow(request)
        except ExternalTimeout as exc:
            self.store.add_attempt(
                workflow["id"],
                action="external_start",
                status="timeout",
                error=str(exc),
                evidence={"ambiguous": True, "request_key": request["request_key"]},
            )
            return self.store.update_workflow(
                workflow["id"],
                state="needs_attention",
                last_error=str(exc),
                recommended_action="reconcile_external_truth",
            )
        except ExternalNonRetryable as exc:
            self.store.add_attempt(workflow["id"], action="external_start", status="non_retryable", error=str(exc))
            return self.store.update_workflow(
                workflow["id"],
                state="needs_attention",
                last_error=str(exc),
                recommended_action="fix_request_before_retry",
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
