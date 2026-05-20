# Evaluator Rubric

Total: 100 points

- Idempotent workflow creation and duplicate external-start prevention: 20
- Durable state transitions and attempt history: 20
- Stale workflow sweeping and recovery queue behavior: 20
- External truth reconciliation under completed, unknown, and non-retryable states: 20
- Operator report quality and evidence: 15
- Code quality, maintainability, and simulator discipline: 5

Major deductions:

- Bypassing Postgres, WireMock, or SQS in the integration path.
- Hardcoding public fixture IDs.
- Treating ambiguous timeout as terminal failure.
- Creating duplicate external jobs under retry.
- Producing reports without external evidence and next actions.

