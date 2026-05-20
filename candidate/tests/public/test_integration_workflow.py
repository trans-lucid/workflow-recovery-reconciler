from __future__ import annotations

from datetime import timedelta

import requests

from load_target import load


external_client = load("src.external_client")
queue_client = load("src.queue_client")
reconciler_module = load("src.reconciler")
runner_module = load("src.runner")
status_report = load("src.status_report")
sweeper_module = load("src.sweeper")
workflow_store = load("src.workflow_store")


def wiremock_post_count() -> int:
    response = requests.post(
        "http://localhost:8089/__admin/requests/count",
        json={"method": "POST", "url": "/external/jobs"},
        timeout=5,
    )
    response.raise_for_status()
    return int(response.json()["count"])


def test_public_docker_workflow_path_uses_state_gateway_and_queue():
    store = workflow_store.PostgresWorkflowStore()
    try:
        store.reset()
        external = external_client.WireMockExternalClient()
        recovery_queue = queue_client.SqsRecoveryQueue()
        runner = runner_module.WorkflowRunner(store, external)
        sweeper = sweeper_module.WorkflowSweeper(store, recovery_queue)
        reconciler = reconciler_module.WorkflowReconciler(store, external, recovery_queue)

        first = runner.start_workflow(
            {
                "request_key": "public-int-001",
                "workflow_type": "workspace_create",
                "resource_id": "workspace-int",
            }
        )
        second = runner.start_workflow(
            {
                "request_key": "public-int-001",
                "workflow_type": "workspace_create",
                "resource_id": "workspace-int",
            }
        )

        assert first["id"] == second["id"], "duplicate_external_start: retry should reuse existing workflow"
        assert store.count_by_request_key("public-int-001") == 1, "duplicate_external_start: duplicate DB workflow rows"
        assert wiremock_post_count() == 1, "duplicate_external_start: WireMock external start was called twice"

        stale = store.create_workflow(
            {
                "request_key": "public-completed",
                "workflow_type": "workspace_create",
                "resource_id": "workspace-completed",
                "state": "running",
                "external_job_id": "wiremock-public-completed",
                "updated_at": workflow_store.utcnow() - timedelta(hours=2),
            }
        )
        sweeper.sweep_stale_workflows(older_than_seconds=60)
        queue_messages = recovery_queue.receive(max_messages=10)
        assert queue_messages, "stale_state_misclassified: stale workflow should be queued for reconciliation"
        for message in queue_messages:
            recovery_queue.delete(message)
            reconciler.reconcile_workflow(message["workflow_id"])

        recovered = store.find_by_id(stale["id"])
        assert recovered["state"] == "complete", "unsafe_retry: external completed truth should win over stale local running state"

        report = status_report.build_status_report(store)
        recovered_report = [item for item in report["workflows"] if item["workflow_id"] == stale["id"]][0]
        assert recovered_report["attempts"], "missing_attempt_history: report should include reconciliation attempt history"
        assert recovered_report["recommended_action"] in {"none", "fulfill", "completed"}, (
            "unsafe_retry: completed workflow report should not ask operators to restart from scratch"
        )
    finally:
        store.close()

