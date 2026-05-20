#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


WORKFLOW_TYPES = ["workspace_create", "document_import", "deployment", "video_pipeline"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260520)
    parser.add_argument("--count", type=int, default=4)
    parser.add_argument("--out", default="candidate/fixtures/public/workflow_events.jsonl")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as handle:
        for index in range(args.count):
            record = {
                "request_key": f"generated-{args.seed}-{index}",
                "workflow_type": rng.choice(WORKFLOW_TYPES),
                "resource_id": f"resource-{index:03d}",
            }
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    print(f"wrote {args.count} workflow events to {out}")


if __name__ == "__main__":
    main()

