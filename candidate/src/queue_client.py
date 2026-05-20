from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError


DEFAULT_QUEUE_NAME = "workflow-recovery"


@dataclass
class InMemoryRecoveryQueue:
    messages: list[dict[str, Any]] = field(default_factory=list)

    def send_recovery(self, payload: dict[str, Any]) -> None:
        self.messages.append(dict(payload))

    def receive(self, max_messages: int = 10) -> list[dict[str, Any]]:
        return list(self.messages[:max_messages])

    def delete(self, message: dict[str, Any]) -> None:
        if message in self.messages:
            self.messages.remove(message)


class SqsRecoveryQueue:
    def __init__(self, queue_name: str = DEFAULT_QUEUE_NAME) -> None:
        endpoint_url = os.environ.get("AWS_ENDPOINT_URL", "http://localhost:4566")
        self.client = boto3.client(
            "sqs",
            endpoint_url=endpoint_url,
            region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "test"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "test"),
        )
        self.queue_url = wait_for_queue(self.client, queue_name)

    def send_recovery(self, payload: dict[str, Any]) -> None:
        self.client.send_message(QueueUrl=self.queue_url, MessageBody=json.dumps(payload))

    def receive(self, max_messages: int = 10) -> list[dict[str, Any]]:
        response = self.client.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=1,
        )
        messages = []
        for raw in response.get("Messages", []):
            body = json.loads(raw["Body"])
            body["_receipt_handle"] = raw["ReceiptHandle"]
            messages.append(body)
        return messages

    def delete(self, message: dict[str, Any]) -> None:
        receipt = message.get("_receipt_handle")
        if receipt:
            self.client.delete_message(QueueUrl=self.queue_url, ReceiptHandle=receipt)


def wait_for_queue(client: Any, queue_name: str, attempts: int = 40, delay_seconds: float = 0.5) -> str:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            try:
                return client.get_queue_url(QueueName=queue_name)["QueueUrl"]
            except ClientError:
                return client.create_queue(QueueName=queue_name)["QueueUrl"]
        except (BotoCoreError, EndpointConnectionError) as exc:
            last_error = exc
            time.sleep(delay_seconds)
    raise RuntimeError("local SQS queue is not ready") from last_error

