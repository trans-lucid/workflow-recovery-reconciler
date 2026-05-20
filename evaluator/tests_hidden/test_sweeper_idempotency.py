from __future__ import annotations

from datetime import timedelta

from src.queue_client import InMemoryRecoveryQueue
from src.sweeper import WorkflowSweeper
from src.workflow_store import InMemoryWorkflowStore, utcnow


def test_two_sweeper_runs_enqueue_one_recovery_action():
    store = InMemoryWorkflowStore()
    workflow = store.create_workflow(
        {
            "request_key": "hidden-stale",
            "workflow_type": "document_import",
            "resource_id": "import-hidden",
            "state": "running",
            "updated_at": utcnow() - timedelta(hours=2),
        }
    )
    queue = InMemoryRecoveryQueue()
    sweeper = WorkflowSweeper(store, queue)

    sweeper.sweep_stale_workflows(older_than_seconds=60)
    sweeper.sweep_stale_workflows(older_than_seconds=60)

    assert len(queue.messages) == 1
    assert len([event for event in store.audit_events(workflow["id"]) if event["event_type"] == "stale_workflow_queued"]) == 1

