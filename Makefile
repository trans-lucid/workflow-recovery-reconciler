PYTHON ?= python3

.PHONY: check-render check-published-repo check-published-repo-after-personalization check-published-repo-after-smoke install validate-solution validate-candidate-main-expected-failure validate-docker-integration validate-rendered-smoke validate-personalization render scan-safety validate clean

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

check-render:
	$(PYTHON) tools/check_render_contract.py

check-published-repo:
	$(PYTHON) tools/check_published_repo_contract.py --candidate-dir generated/main --solution-dir generated/solution --manifest translucid-template.json

check-published-repo-after-personalization:
	$(MAKE) check-published-repo

check-published-repo-after-smoke:
	$(MAKE) check-published-repo

validate-personalization:
	$(PYTHON) tools/validate_personalization.py

validate: validate-solution validate-candidate-main-expected-failure render check-render check-published-repo scan-safety validate-personalization check-published-repo-after-personalization validate-rendered-smoke check-published-repo-after-smoke validate-docker-integration

clean:
	rm -rf generated
	cd candidate && docker compose down -v || true
