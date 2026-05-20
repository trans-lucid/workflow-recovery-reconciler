from __future__ import annotations

from datetime import timedelta

from src.external_client import FakeExternalClient
from src.queue_client import InMemoryRecoveryQueue
from src.reconciler import WorkflowReconciler
from src.runner import WorkflowRunner
from src.sweeper import WorkflowSweeper
from src.workflow_store import InMemoryWorkflowStore, utcnow


def test_reference_solution_recovers_stale_completed_workflow():
    store = InMemoryWorkflowStore()
    external = FakeExternalClient(
        statuses={
            "sol-complete": {
                "external_job_id": "ext-sol-complete",
                "state": "completed",
                "evidence": "control-plane completion record",
            }
        }
    )
    queue = InMemoryRecoveryQueue()
    runner = WorkflowRunner(store, external)
    first = runner.start_workflow(
        {
            "request_key": "sol-complete",
            "workflow_type": "workspace_create",
            "resource_id": "workspace-sol",
        }
    )
    second = runner.start_workflow(
        {
            "request_key": "sol-complete",
            "workflow_type": "workspace_create",
            "resource_id": "workspace-sol",
        }
    )
    assert first["id"] == second["id"]
    store.update_workflow(first["id"], updated_at=utcnow() - timedelta(hours=1))

    WorkflowSweeper(store, queue).sweep_stale_workflows(older_than_seconds=60)
    assert len(queue.messages) == 1

    reconciler = WorkflowReconciler(store, external, queue)
    reconciler.drain_recovery_queue()
    assert store.find_by_id(first["id"])["state"] == "complete"

