PYTHON ?= python3

.PHONY: install validate-solution validate-candidate-main-expected-failure validate-docker-integration validate-rendered-smoke render scan-safety validate clean

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e "candidate[test]"

validate-solution: install
	EVAL_TARGET="$(PWD)/solution" $(PYTHON) -m pytest candidate/tests/public/test_unit_contract.py solution/tests evaluator/tests_hidden

validate-candidate-main-expected-failure: install
	bash tools/expect_candidate_failure.sh

validate-docker-integration: install
	bash tools/expect_candidate_docker_failure.sh

validate-rendered-smoke: render scan-safety
	bash tools/validate_rendered_smoke.sh

render:
	$(PYTHON) tools/render_template.py

scan-safety:
	$(PYTHON) tools/scan_safety.py

validate: validate-solution validate-candidate-main-expected-failure render scan-safety validate-rendered-smoke validate-docker-integration

clean:
	rm -rf generated
	cd candidate && docker compose down -v || true

