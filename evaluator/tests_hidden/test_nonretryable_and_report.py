from __future__ import annotations

from src.external_client import FakeExternalClient
from src.reconciler import WorkflowReconciler
from src.status_report import build_status_report
from src.workflow_store import InMemoryWorkflowStore


def test_nonretryable_external_error_requires_attention():
    store = InMemoryWorkflowStore()
    workflow = store.create_workflow(
        {
            "request_key": "hidden-invalid",
            "workflow_type": "workspace_create",
            "resource_id": "workspace-invalid",
            "state": "started",
        }
    )
    external = FakeExternalClient(
        statuses={
            "hidden-invalid": {
                "external_job_id": "ext-invalid",
                "state": "non_retryable",
                "evidence": "quota policy rejected request",
            }
        }
    )
    result = WorkflowReconciler(store, external).reconcile_workflow(workflow["id"])
    assert result["state"] == "needs_attention"
    assert result["recommended_action"] == "fix_request_before_retry"


def test_operator_report_identifies_blocker_and_next_action():
    store = InMemoryWorkflowStore()
    workflow = store.create_workflow(
        {
            "request_key": "hidden-report",
            "workflow_type": "video_pipeline",
            "resource_id": "video-1",
            "state": "started",
        }
    )
    WorkflowReconciler(store, FakeExternalClient()).reconcile_workflow(workflow["id"])
    report = build_status_report(store)
    item = report["workflows"][0]
    assert item["blocker"]
    assert item["next_action"] == "check_external_truth"
    assert item["external_evidence"]

