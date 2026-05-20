from __future__ import annotations

from src.external_client import FakeExternalClient
from src.reconciler import WorkflowReconciler
from src.workflow_store import InMemoryWorkflowStore


def test_external_completed_beats_local_running_state():
    store = InMemoryWorkflowStore()
    workflow = store.create_workflow(
        {
            "request_key": "hidden-complete",
            "workflow_type": "workspace_create",
            "resource_id": "workspace-hidden",
            "state": "running",
            "external_job_id": "ext-hidden",
        }
    )
    external = FakeExternalClient(
        statuses={
            "hidden-complete": {
                "external_job_id": "ext-hidden",
                "state": "completed",
                "evidence": "external audit says complete",
            }
        }
    )
    result = WorkflowReconciler(store, external).reconcile_workflow(workflow["id"])
    assert result["state"] == "complete"


def test_unknown_external_truth_goes_to_attention_not_retry_loop():
    store = InMemoryWorkflowStore()
    workflow = store.create_workflow(
        {
            "request_key": "hidden-unknown",
            "workflow_type": "workspace_create",
            "resource_id": "workspace-unknown",
            "state": "started",
        }
    )
    result = WorkflowReconciler(store, FakeExternalClient()).reconcile_workflow(workflow["id"])
    assert result["state"] == "needs_attention"
    assert result["recommended_action"] == "check_external_truth"

