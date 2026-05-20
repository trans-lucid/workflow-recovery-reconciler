# Source Dossier: Workflow Recovery Reconciler

## Sources Studied

- Temporal workflow/activity retry and local development concepts.
- Testcontainers and Docker Compose patterns for disposable integration dependencies.
- WireMock local HTTP fault injection patterns.
- LocalStack SQS local queue patterns.
- Production control-plane incident patterns around stuck jobs, stale leases, and external truth reconciliation.

## Allowed Reuse

- Architecture ideas around durable workflow state, attempts, retries, leases, and reconciliation.
- Generic terminology such as workflow, activity, attempt, lease, sweeper, reconciler, and dead-letter queue.
- Local emulator patterns for HTTP services and queues.
- Test ideas around timeouts, stale state, duplicate starts, and unknown external truth.

## Forbidden

- Copying Temporal, WireMock, LocalStack, or customer source code.
- Copying complete exercises, datasets, or proprietary incidents.
- Requiring live Temporal Cloud, AWS, or any external credentials.
- Including real customer data, production configuration, or customer source paths.

