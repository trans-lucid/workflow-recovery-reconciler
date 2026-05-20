from __future__ import annotations

from src.external_client import FakeExternalClient
from src.reconciler import WorkflowReconciler
from src.runner import WorkflowRunner
from src.workflow_store import InMemoryWorkflowStore


def test_timeout_then_reconcile_preserves_attempt_history():
    store = InMemoryWorkflowStore()
    external = FakeExternalClient(start_behaviors={"hidden-timeout": "timeout"})
    runner = WorkflowRunner(store, external)
    workflow = runner.start_workflow(
        {
            "request_key": "hidden-timeout",
            "workflow_type": "deployment",
            "resource_id": "deploy-1",
        }
    )
    external.statuses["hidden-timeout"] = {
        "external_job_id": "ext-hidden-timeout",
        "state": "completed",
        "evidence": "created before timeout and later completed",
    }

    result = WorkflowReconciler(store, external).reconcile_workflow(workflow["id"])
    attempts = store.attempts_for_workflow(workflow["id"])

    assert result["state"] == "complete"
    assert [attempt["action"] for attempt in attempts] == ["external_start", "external_status"]
    assert attempts[0]["status"] == "timeout"
    assert attempts[1]["status"] == "completed"

