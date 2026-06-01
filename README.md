# Workflow Recovery Reconciler

This is an internal Translucid challenge template, not a generated candidate repo.

The template generates a production-shaped backend challenge for long-running control-plane workflows that can get stuck between local state, external service truth, retry queues, and operator visibility. It is designed for backend, platform, infrastructure, and Staff-level candidates working on workspace creation, VM provisioning, background imports, document processing, deployment jobs, or GPU workspace startup.

The generated candidate repo intentionally contains flawed starter code. Candidates must repair durable workflow state, retry-safe reconciliation, stale workflow sweeping, partial failure recovery, and operator-readable status reporting.

## Local Simulator

Candidate and evaluator validation use local services only:

- Postgres stores workflow state, attempts, leases, and audit logs.
- WireMock simulates an external control-plane service with running, completed, unknown, timeout, and non-retryable responses.
- LocalStack SQS simulates a recovery queue used by the stale workflow sweeper and reconciler.

No external credentials, cloud accounts, Temporal Cloud, customer data, or startup source code are required.

## Template Contract

Generated candidate main includes only:

- Candidate README and DEBRIEF
- Runnable Python starter repo
- Public fixtures and public tests
- Docker Compose local simulator
- Makefile commands

Hidden evaluator material, solution code, rubrics, expected outputs, source dossiers, and internal metadata stay out of generated candidate main.

## Validation

Root validation gates:

```bash
make validate-solution
make validate-candidate-main-expected-failure
make render
make check-render
make check-published-repo
make scan-safety
make validate-personalization
make validate-rendered-smoke
make validate-docker-integration
make validate
```

Expected starter failure markers:

- `duplicate_external_start`
- `stale_state_misclassified`
- `missing_attempt_history`
- `unsafe_retry`

## For Challenge Creation Agents

Do not infer how to use this template from README prose.

Read `translucid-template.json`.

Normal use:

```bash
make render
make check-render
make check-published-repo
make scan-safety
make validate-personalization
make validate-solution
make validate-candidate-main-expected-failure
make validate-docker-integration
```

Use:

- `generated/main` as candidate-facing main branch
- `generated/solution` as private solution/evaluator branch

Do not manually copy `candidate/` to root.
Do not manually restructure `solution/`.
Do not edit hidden tests or evaluator imports unless a validation command fails and the exact blocker is recorded.
