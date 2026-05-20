from __future__ import annotations

from datetime import timedelta

from load_target import load


external_client = load("src.external_client")
queue_client = load("src.queue_client")
runner_module = load("src.runner")
status_report = load("src.status_report")
sweeper_module = load("src.sweeper")
workflow_store = load("src.workflow_store")


def request(request_key: str = "public-unit-001") -> dict:
    return {
        "request_key": request_key,
        "workflow_type": "workspace_create",
        "resource_id": "workspace-alpha",
    }


def test_duplicate_start_request_is_idempotent():
    store = workflow_store.InMemoryWorkflowStore()
    external = external_client.FakeExternalClient()
    runner = runner_module.WorkflowRunner(store, external)

    first = runner.start_workflow(request("dup-key"))
    second = runner.start_workflow(request("dup-key"))

    assert first["id"] == second["id"], "duplicate_external_start: repeated request_key must reuse existing workflow"
    assert store.count_by_request_key("dup-key") == 1, "duplicate_external_start: duplicate local workflow rows were created"
    assert len(external.start_calls) == 1, "duplicate_external_start: external service was started more than once"


def test_stale_started_workflow_is_recovery_work_not_failure():
    store = workflow_store.InMemoryWorkflowStore()
    stale = store.create_workflow(
        {
            "request_key": "stale-key",
            "workflow_type": "workspace_create",
            "resource_id": "workspace-stale",
            "state": "running",
            "external_job_id": "ext-stale",
            "updated_at": workflow_store.utcnow() - timedelta(hours=2),
        }
    )
    queue = queue_client.InMemoryRecoveryQueue()
    sweeper = sweeper_module.WorkflowSweeper(store, queue)

    actions = sweeper.sweep_stale_workflows(older_than_seconds=60)
    updated = store.find_by_id(stale["id"])

    assert actions, "stale_state_misclassified: stale workflow was not detected"
    assert updated["state"] != "failed", "stale_state_misclassified: stale workflow was failed before external truth was checked"
    assert queue.messages, "stale_state_misclassified: stale workflow should enqueue reconciliation work"


def test_timeout_preserves_attempt_history_for_reconciliation():
    store = workflow_store.InMemoryWorkflowStore()
    external = external_client.FakeExternalClient(start_behaviors={"timeout-key": "timeout"})
    runner = runner_module.WorkflowRunner(store, external)

    workflow = runner.start_workflow(request("timeout-key"))
    attempts = store.attempts_for_workflow(workflow["id"])

    failures = []
    if not attempts:
        failures.append("missing_attempt_history: timeout path must record an external attempt")
    if workflow["state"] not in {"started", "running", "needs_attention"}:
        failures.append("unsafe_retry: timeout is ambiguous and must not be marked terminally failed without reconciliation")
    assert not failures, "; ".join(failures)


def test_status_report_schema_is_machine_readable():
    store = workflow_store.InMemoryWorkflowStore()
    workflow = store.create_workflow(
        {
            "request_key": "report-key",
            "workflow_type": "import",
            "resource_id": "import-1",
            "state": "needs_attention",
            "recommended_action": "check_external_truth",
        }
    )
    store.add_attempt(workflow["id"], action="external_status", status="unknown", evidence={"source": "unit"})
    report = status_report.build_status_report(store)

    assert report["schema_version"] == "workflow-recovery-report/v1"
    assert report["summary"]["total_workflows"] == 1
    assert report["workflows"][0]["workflow_id"] == workflow["id"]
    assert "recommended_action" in report["workflows"][0]
