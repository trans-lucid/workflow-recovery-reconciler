# Workflow Recovery Reconciler

You are inheriting a control-plane service where long-running workflows can become inconsistent after timeouts, retries, stale leases, and ambiguous external status.

Repair the production path across the runner, sweeper, reconciler, store, and report code. The final implementation should create workflows idempotently, preserve attempt history, reconcile local state against external truth, avoid duplicate external starts/actions, and write an operator-readable report.

## Local Services

```txt
Postgres       workflow state, attempts, leases, audit log
WireMock       fake external control-plane API
LocalStack SQS recovery queue
```

No real cloud credentials or external services are needed.

## Commands

```bash
make dev
make seed
make test
make test-integration
make run
make clean
```

## Deliverables

- Passing public tests.
- `results/workflow_recovery_report.json`
- `results/summary.md`

Private tests use harder workflow histories, external truth ambiguity, concurrent sweepers, and duplicate retry cases. Do not hardcode fixture IDs or bypass the local simulator.

