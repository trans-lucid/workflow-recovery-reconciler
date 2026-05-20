from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import requests


class ExternalTimeout(RuntimeError):
    pass


class ExternalNonRetryable(RuntimeError):
    pass


@dataclass
class FakeExternalClient:
    statuses: dict[str, dict[str, Any]] = field(default_factory=dict)
    start_behaviors: dict[str, str] = field(default_factory=dict)
    start_calls: list[dict[str, Any]] = field(default_factory=list)

    def start_workflow(self, request: dict[str, Any]) -> dict[str, Any]:
        request_key = request["request_key"]
        self.start_calls.append(dict(request))
        behavior = self.start_behaviors.get(request_key, "success")
        external_job_id = f"ext-{request_key}-{len(self.start_calls)}"
        if behavior == "timeout":
            self.statuses.setdefault(
                request_key,
                {"external_job_id": external_job_id, "state": "running", "evidence": "created-before-timeout"},
            )
            raise ExternalTimeout("external service timed out after accepting the job")
        if behavior == "nonretryable":
            raise ExternalNonRetryable("invalid workflow request")
        response = {"external_job_id": external_job_id, "state": "running", "evidence": "accepted"}
        self.statuses.setdefault(request_key, response)
        return response

    def get_workflow_status(self, request_key: str, external_job_id: str | None = None) -> dict[str, Any]:
        return self.statuses.get(
            request_key,
            {"external_job_id": external_job_id, "state": "unknown", "evidence": "no-external-record"},
        )


class WireMockExternalClient:
    def __init__(self, base_url: str = "http://localhost:8089", timeout_seconds: float = 2.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        wait_for_http(f"{self.base_url}/__admin/health")

    def start_workflow(self, request: dict[str, Any]) -> dict[str, Any]:
        try:
            response = requests.post(
                f"{self.base_url}/external/jobs",
                json=request,
                timeout=self.timeout_seconds,
            )
        except requests.Timeout as exc:
            raise ExternalTimeout("external service timed out") from exc
        if response.status_code in {408, 504}:
            raise ExternalTimeout(f"external service returned timeout status {response.status_code}")
        if response.status_code in {400, 409, 422}:
            raise ExternalNonRetryable(response.text)
        if response.status_code >= 500:
            raise ExternalTimeout(f"external service returned retryable status {response.status_code}")
        response.raise_for_status()
        return response.json()

    def get_workflow_status(self, request_key: str, external_job_id: str | None = None) -> dict[str, Any]:
        response = requests.get(
            f"{self.base_url}/external/jobs/by-key/{request_key}",
            params={"external_job_id": external_job_id or ""},
            timeout=self.timeout_seconds,
        )
        if response.status_code == 404:
            return {"external_job_id": external_job_id, "state": "unknown", "evidence": "not-found"}
        response.raise_for_status()
        return response.json()


def wait_for_http(url: str, attempts: int = 40, delay_seconds: float = 0.5) -> None:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            response = requests.get(url, timeout=2)
            if response.status_code < 500:
                return
        except requests.RequestException as exc:
            last_error = exc
        time.sleep(delay_seconds)
    raise RuntimeError(f"http service not ready at {url}") from last_error

