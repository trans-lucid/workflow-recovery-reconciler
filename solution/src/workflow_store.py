from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row


DEFAULT_DATABASE_URL = "postgres://postgres:postgres@localhost:5432/workflows"
MIGRATION_PATH = Path(__file__).resolve().parents[1] / "migrations" / "001_init.sql"


def utcnow() -> datetime:
    return datetime.now(UTC)


def parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def serialize_record(record: dict[str, Any] | None) -> dict[str, Any] | None:
    if record is None:
        return None
    serialized: dict[str, Any] = {}
    for key, value in record.items():
        if isinstance(value, datetime):
            serialized[key] = value.isoformat()
        else:
            serialized[key] = value
    return serialized


class InMemoryWorkflowStore:
    def __init__(self) -> None:
        self.workflows: list[dict[str, Any]] = []
        self.attempts: list[dict[str, Any]] = []
        self.audit: list[dict[str, Any]] = []

    def close(self) -> None:
        return None

    def reset(self) -> None:
        self.workflows.clear()
        self.attempts.clear()
        self.audit.clear()

    def create_workflow(self, workflow: dict[str, Any]) -> dict[str, Any]:
        now = utcnow()
        record = {
            "id": workflow.get("id") or str(uuid.uuid4()),
            "request_key": workflow["request_key"],
            "workflow_type": workflow["workflow_type"],
            "resource_id": workflow["resource_id"],
            "state": workflow.get("state", "started"),
            "external_job_id": workflow.get("external_job_id"),
            "requested_at": parse_dt(workflow.get("requested_at")) or now,
            "updated_at": parse_dt(workflow.get("updated_at")) or now,
            "lease_expires_at": parse_dt(workflow.get("lease_expires_at")),
            "last_error": workflow.get("last_error"),
            "last_external_state": workflow.get("last_external_state"),
            "recommended_action": workflow.get("recommended_action"),
        }
        self.workflows.append(record)
        return deepcopy(record)

    def find_by_id(self, workflow_id: str) -> dict[str, Any] | None:
        for record in self.workflows:
            if record["id"] == workflow_id:
                return deepcopy(record)
        return None

    def find_by_request_key(self, request_key: str) -> dict[str, Any] | None:
        for record in self.workflows:
            if record["request_key"] == request_key:
                return deepcopy(record)
        return None

    def count_by_request_key(self, request_key: str) -> int:
        return sum(1 for record in self.workflows if record["request_key"] == request_key)

    def update_workflow(self, workflow_id: str, **fields: Any) -> dict[str, Any]:
        for record in self.workflows:
            if record["id"] == workflow_id:
                for key, value in fields.items():
                    record[key] = parse_dt(value) if key.endswith("_at") else value
                record["updated_at"] = parse_dt(fields.get("updated_at")) or utcnow()
                return deepcopy(record)
        raise KeyError(f"unknown workflow {workflow_id}")

    def add_attempt(
        self,
        workflow_id: str,
        *,
        action: str,
        status: str,
        external_job_id: str | None = None,
        error: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        attempt_no = len([a for a in self.attempts if a["workflow_id"] == workflow_id]) + 1
        record = {
            "id": len(self.attempts) + 1,
            "workflow_id": workflow_id,
            "attempt_no": attempt_no,
            "action": action,
            "status": status,
            "external_job_id": external_job_id,
            "error": error,
            "evidence": evidence or {},
            "created_at": utcnow(),
        }
        self.attempts.append(record)
        return deepcopy(record)

    def attempts_for_workflow(self, workflow_id: str) -> list[dict[str, Any]]:
        return [deepcopy(a) for a in self.attempts if a["workflow_id"] == workflow_id]

    def append_audit(
        self,
        workflow_id: str,
        *,
        event_type: str,
        details: dict[str, Any] | None = None,
        event_key: str | None = None,
    ) -> dict[str, Any]:
        if event_key is not None:
            for record in self.audit:
                if record["workflow_id"] == workflow_id and record["event_key"] == event_key:
                    return deepcopy(record)
        record = {
            "id": len(self.audit) + 1,
            "workflow_id": workflow_id,
            "event_key": event_key,
            "event_type": event_type,
            "details": details or {},
            "created_at": utcnow(),
        }
        self.audit.append(record)
        return deepcopy(record)

    def audit_events(self, workflow_id: str) -> list[dict[str, Any]]:
        return [deepcopy(a) for a in self.audit if a["workflow_id"] == workflow_id]

    def list_stale(self, *, older_than_seconds: int, states: set[str] | None = None) -> list[dict[str, Any]]:
        cutoff = utcnow() - timedelta(seconds=older_than_seconds)
        target_states = states or {"started", "running"}
        return [
            deepcopy(record)
            for record in self.workflows
            if record["state"] in target_states and parse_dt(record["updated_at"]) < cutoff
        ]

    def list_workflows(self) -> list[dict[str, Any]]:
        return [deepcopy(record) for record in self.workflows]


class PostgresWorkflowStore:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
        self.conn = wait_for_postgres(self.database_url)

    def close(self) -> None:
        self.conn.close()

    def reset(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute("TRUNCATE workflow_audit, workflow_attempts, workflows RESTART IDENTITY CASCADE")
        self.conn.commit()

    def migrate(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute(MIGRATION_PATH.read_text())
        self.conn.commit()

    def create_workflow(self, workflow: dict[str, Any]) -> dict[str, Any]:
        record = {
            "id": workflow.get("id") or str(uuid.uuid4()),
            "request_key": workflow["request_key"],
            "workflow_type": workflow["workflow_type"],
            "resource_id": workflow["resource_id"],
            "state": workflow.get("state", "started"),
            "external_job_id": workflow.get("external_job_id"),
            "requested_at": parse_dt(workflow.get("requested_at")) or utcnow(),
            "updated_at": parse_dt(workflow.get("updated_at")) or utcnow(),
            "lease_expires_at": parse_dt(workflow.get("lease_expires_at")),
            "last_error": workflow.get("last_error"),
            "last_external_state": workflow.get("last_external_state"),
            "recommended_action": workflow.get("recommended_action"),
        }
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO workflows (
                  id, request_key, workflow_type, resource_id, state, external_job_id,
                  requested_at, updated_at, lease_expires_at, last_error, last_external_state,
                  recommended_action
                )
                VALUES (
                  %(id)s, %(request_key)s, %(workflow_type)s, %(resource_id)s, %(state)s,
                  %(external_job_id)s, %(requested_at)s, %(updated_at)s, %(lease_expires_at)s,
                  %(last_error)s, %(last_external_state)s, %(recommended_action)s
                )
                RETURNING *
                """,
                record,
            )
            inserted = dict(cur.fetchone())
        self.conn.commit()
        return inserted

    def find_by_id(self, workflow_id: str) -> dict[str, Any] | None:
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM workflows WHERE id = %s", (workflow_id,))
            row = cur.fetchone()
        return dict(row) if row else None

    def find_by_request_key(self, request_key: str) -> dict[str, Any] | None:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM workflows WHERE request_key = %s ORDER BY requested_at ASC LIMIT 1",
                (request_key,),
            )
            row = cur.fetchone()
        return dict(row) if row else None

    def count_by_request_key(self, request_key: str) -> int:
        with self.conn.cursor() as cur:
            cur.execute("SELECT count(*) AS count FROM workflows WHERE request_key = %s", (request_key,))
            return int(cur.fetchone()["count"])

    def update_workflow(self, workflow_id: str, **fields: Any) -> dict[str, Any]:
        allowed = {
            "state",
            "external_job_id",
            "lease_expires_at",
            "last_error",
            "last_external_state",
            "recommended_action",
            "updated_at",
        }
        update_fields = {key: value for key, value in fields.items() if key in allowed}
        update_fields["updated_at"] = parse_dt(update_fields.get("updated_at")) or utcnow()
        assignments = ", ".join(f"{key} = %({key})s" for key in update_fields)
        params = update_fields | {"id": workflow_id}
        with self.conn.cursor() as cur:
            cur.execute(f"UPDATE workflows SET {assignments} WHERE id = %(id)s RETURNING *", params)
            row = cur.fetchone()
        self.conn.commit()
        if not row:
            raise KeyError(f"unknown workflow {workflow_id}")
        return dict(row)

    def add_attempt(
        self,
        workflow_id: str,
        *,
        action: str,
        status: str,
        external_job_id: str | None = None,
        error: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT COALESCE(MAX(attempt_no), 0) + 1 AS next_no FROM workflow_attempts WHERE workflow_id = %s", (workflow_id,))
            attempt_no = int(cur.fetchone()["next_no"])
            cur.execute(
                """
                INSERT INTO workflow_attempts (
                  workflow_id, attempt_no, action, status, external_job_id, error, evidence
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                RETURNING *
                """,
                (
                    workflow_id,
                    attempt_no,
                    action,
                    status,
                    external_job_id,
                    error,
                    json.dumps(evidence or {}),
                ),
            )
            row = cur.fetchone()
        self.conn.commit()
        return dict(row)

    def attempts_for_workflow(self, workflow_id: str) -> list[dict[str, Any]]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM workflow_attempts WHERE workflow_id = %s ORDER BY attempt_no", (workflow_id,))
            return [dict(row) for row in cur.fetchall()]

    def append_audit(
        self,
        workflow_id: str,
        *,
        event_type: str,
        details: dict[str, Any] | None = None,
        event_key: str | None = None,
    ) -> dict[str, Any]:
        with self.conn.cursor() as cur:
            if event_key is not None:
                cur.execute(
                    "SELECT * FROM workflow_audit WHERE workflow_id = %s AND event_key = %s LIMIT 1",
                    (workflow_id, event_key),
                )
                existing = cur.fetchone()
                if existing:
                    return dict(existing)
            cur.execute(
                """
                INSERT INTO workflow_audit (workflow_id, event_key, event_type, details)
                VALUES (%s, %s, %s, %s::jsonb)
                RETURNING *
                """,
                (workflow_id, event_key, event_type, json.dumps(details or {})),
            )
            row = cur.fetchone()
        self.conn.commit()
        return dict(row)

    def audit_events(self, workflow_id: str) -> list[dict[str, Any]]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM workflow_audit WHERE workflow_id = %s ORDER BY id", (workflow_id,))
            return [dict(row) for row in cur.fetchall()]

    def list_stale(self, *, older_than_seconds: int, states: set[str] | None = None) -> list[dict[str, Any]]:
        target_states = list(states or {"started", "running"})
        cutoff = utcnow() - timedelta(seconds=older_than_seconds)
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM workflows WHERE state = ANY(%s) AND updated_at < %s ORDER BY updated_at ASC",
                (target_states, cutoff),
            )
            return [dict(row) for row in cur.fetchall()]

    def list_workflows(self) -> list[dict[str, Any]]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM workflows ORDER BY requested_at ASC")
            return [dict(row) for row in cur.fetchall()]


def wait_for_postgres(database_url: str, attempts: int = 40, delay_seconds: float = 0.5) -> psycopg.Connection:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            return psycopg.connect(database_url, row_factory=dict_row)
        except psycopg.OperationalError as exc:
            last_error = exc
            time.sleep(delay_seconds)
    raise RuntimeError(f"postgres not ready at {database_url}") from last_error


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["migrate", "reset"])
    args = parser.parse_args()
    store = PostgresWorkflowStore()
    try:
        if args.command == "migrate":
            store.migrate()
            print("postgres migration complete")
        else:
            store.reset()
            print("postgres state reset")
    finally:
        store.close()


if __name__ == "__main__":
    main()
