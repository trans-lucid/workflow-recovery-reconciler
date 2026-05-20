from __future__ import annotations

from src.workflow_store import PostgresWorkflowStore


def main() -> None:
    store = PostgresWorkflowStore()
    try:
        store.reset()
        print("workflow database reset")
    finally:
        store.close()


if __name__ == "__main__":
    main()

