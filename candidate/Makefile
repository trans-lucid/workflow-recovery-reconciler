.PHONY: dev logs seed test test-unit test-integration run clean

PYTHON ?= python3

dev:
	docker compose up -d

logs:
	docker compose logs -f

seed:
	$(PYTHON) -m src.workflow_store migrate
	$(PYTHON) -m scripts.setup_gateway
	$(PYTHON) -m scripts.setup_queue
	$(PYTHON) -m scripts.reset_state

test:
	$(PYTHON) -m pytest tests/public

test-unit:
	$(PYTHON) -m pytest tests/public/test_unit_contract.py

test-integration:
	$(PYTHON) -m pytest tests/public/test_integration_workflow.py

run:
	$(PYTHON) -m src.main --report results/workflow_recovery_report.json

clean:
	docker compose down -v

