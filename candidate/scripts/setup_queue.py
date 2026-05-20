from __future__ import annotations

import os
import time

import boto3
from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError


QUEUE_NAME = "workflow-recovery"


def client():
    return boto3.client(
        "sqs",
        endpoint_url=os.environ.get("AWS_ENDPOINT_URL", "http://localhost:4566"),
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "test"),
    )


def main() -> None:
    sqs = client()
    last_error: Exception | None = None
    for _ in range(40):
        try:
            queue_url = sqs.create_queue(QueueName=QUEUE_NAME)["QueueUrl"]
            try:
                sqs.purge_queue(QueueUrl=queue_url)
            except ClientError:
                pass
            print(f"local SQS queue ready: {queue_url}")
            return
        except (BotoCoreError, EndpointConnectionError) as exc:
            last_error = exc
            time.sleep(0.5)
    raise RuntimeError("local SQS was not ready") from last_error


if __name__ == "__main__":
    main()

