from __future__ import annotations

import time

import requests


WIREMOCK = "http://localhost:8089"


def wait_for_wiremock() -> None:
    last_error: Exception | None = None
    for _ in range(40):
        try:
            response = requests.get(f"{WIREMOCK}/__admin", timeout=2)
            if response.status_code < 500:
                return
        except requests.RequestException as exc:
            last_error = exc
        time.sleep(0.5)
    raise RuntimeError("wiremock was not ready") from last_error


def add_mapping(mapping: dict) -> None:
    response = requests.post(f"{WIREMOCK}/__admin/mappings", json=mapping, timeout=5)
    response.raise_for_status()


def main() -> None:
    wait_for_wiremock()
    requests.post(f"{WIREMOCK}/__admin/reset", timeout=5).raise_for_status()

    add_mapping(
        {
            "priority": 1,
            "request": {"method": "POST", "url": "/external/jobs"},
            "response": {
                "status": 200,
                "headers": {"Content-Type": "application/json"},
                "transformers": ["response-template"],
                "jsonBody": {
                    "external_job_id": "wiremock-{{jsonPath request.body '$.request_key'}}",
                    "state": "running",
                    "evidence": "wiremock accepted start for {{jsonPath request.body '$.request_key'}}",
                },
            },
        }
    )

    add_mapping(
        {
            "priority": 1,
            "request": {"method": "GET", "urlPath": "/external/jobs/by-key/public-completed"},
            "response": {
                "status": 200,
                "headers": {"Content-Type": "application/json"},
                "jsonBody": {
                    "external_job_id": "wiremock-public-completed",
                    "state": "completed",
                    "evidence": "external service reports completion",
                },
            },
        }
    )

    add_mapping(
        {
            "priority": 10,
            "request": {"method": "GET", "urlPathPattern": "/external/jobs/by-key/.*"},
            "response": {
                "status": 200,
                "headers": {"Content-Type": "application/json"},
                "jsonBody": {
                    "external_job_id": "unknown",
                    "state": "unknown",
                    "evidence": "no matching external record",
                },
            },
        }
    )
    print("wiremock external service mappings ready")


if __name__ == "__main__":
    main()

