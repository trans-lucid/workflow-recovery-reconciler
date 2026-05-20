from __future__ import annotations

import argparse

from src.external_client import WireMockExternalClient
from src.queue_client import SqsRecoveryQueue
from src.reconciler import WorkflowReconciler
from src.runner import WorkflowRunner
from src.status_report import write_status_report
from src.sweeper import WorkflowSweeper
from src.workflow_store import PostgresWorkflowStore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="results/workflow_recovery_report.json")
    args = parser.parse_args()

    store = PostgresWorkflowStore()
    try:
        external = WireMockExternalClient()
        queue = SqsRecoveryQueue()
        runner = WorkflowRunner(store, external)
        sweeper = WorkflowSweeper(store, queue)
        reconciler = WorkflowReconciler(store, external, queue)

        runner.start_workflow(
            {
                "request_key": "demo-workspace-001",
                "workflow_type": "workspace_create",
                "resource_id": "workspace-demo",
            }
        )
        sweeper.sweep_stale_workflows(older_than_seconds=0)
        reconciler.drain_recovery_queue()
        report = write_status_report(store, args.report)
        print(f"wrote report with {report['summary']['total_workflows']} workflows to {args.report}")
    finally:
        store.close()


if __name__ == "__main__":
    main()

