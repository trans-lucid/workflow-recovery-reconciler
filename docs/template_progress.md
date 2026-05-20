# Template Progress

| # | Template | Status | Coverage | Local services | Validation | Remote CI | Notes |
| -: | --- | --- | --- | --- | --- | --- | --- |
| 1 | async-webhook-ledger | golden | inbound event idempotency | Postgres, LocalStack SQS, WireMock, MailHog | passed in prior repo | passed in prior repo | First golden backend reliability template |
| 2 | rag-retrieval-quality-lab | golden | AI retrieval quality | Qdrant, Postgres, MinIO, fake embedding API | passed in prior repo | passed in prior repo | Second golden AI backend template |
| 3 | gpu-fault-correlation-drain-scheduler | golden-template-candidate | ML infra cluster operations | telemetry simulator, control-plane simulator | passed in prior repo | passed in prior repo | Fresh-clone proof handled separately |
| 4 | streaming-chat-budget-tools | golden-template-candidate | full-stack AI streaming | local fake model/tool simulator | passed in prior repo | passed in prior repo | UI-level gate added before golden |
| 5 | agent-trace-evaluator | golden-template-candidate | AI agent evals | fake trace API, Jaeger | passed in prior repo | passed in prior repo | Fresh-clone proof handled separately |
| 6 | payment-recovery-state-machine | golden | fintech backend recovery | Postgres, WireMock, LocalStack SQS, MailHog | passed | passed | Distinct from inbound webhook ledger |
| 7 | workflow-recovery-reconciler | golden | backend/platform workflow recovery | Postgres, WireMock, LocalStack SQS | passed | passed | Fresh-clone proof passed |
## Machine-Readable Contract Migration

- machine_readable_manifest: present
- root_make_aliases: present
- render_context_support: present
- check_render_contract: present
- scan_safety_uses_manifest: present
- remote_ci_manifest_validation: passed

