# Template Rules And Build Instructions

These rules apply to every Translucid internal challenge template, including `async-webhook-ledger`, `rag-retrieval-quality-lab`, and all future templates in the library.

## Purpose

- Build internal template repos, not one-off candidate challenge repos.
- Use public sources only as reference architecture, not copied assessments or copied implementations.
- Generate original Translucid-owned code, fixtures, tests, docs, and rubrics.
- Recruiter source repos may personalize generated challenges, but they must not become the challenge repo unless an explicit source-slice mode is approved.
- Templates should produce realistic production-shaped interview repos with public tests, hidden evaluator tests, local simulators, and safe generated candidate branches.

## Required Repo Shape

Each template repo should include:

- `README.md`: internal template overview.
- `README.md.j2`: candidate-facing generated README.
- `DEBRIEF.md.j2`: candidate-facing debrief questions.
- `template.yaml`: template metadata, local service contract, roles, time, signals, expected starter failures, and hidden-test strategy.
- `candidate/`: runnable starter repo with public tests only.
- `solution/`: reference implementation, solution notes, and expected outputs.
- `evaluator/`: hidden tests, hidden fixtures, rubric, evaluator compose file, and evaluator scripts.
- `generators/`: deterministic fixture generator and scenario definitions.
- `metadata/`: source mapping rules and safety policy.
- `source-dossiers/`: source-inspiration notes and reuse boundaries.
- `tools/`: render, safety scan, and expected-failure validation scripts.
- `.github/workflows/template-validation.yml`: remote CI validation.
- `docs/template_rules.md`: reusable rules for future templates.
- `docs/template_progress.md`: template library progress tracker.

## Candidate Main Contract

- Candidate main must be clean and candidate-safe.
- Candidate main must include a runnable repo, public tests, stubs or flawed starter code, fixtures, README, DEBRIEF, local simulator config, and commands.
- Candidate main must not include hidden tests, hidden fixtures, evaluator material, solution code, `SOLUTION.md`, rubrics, source dossiers, internal metadata, or expected private outputs.
- Candidate work must exercise a realistic production path across multiple files.
- Do not make the task solvable by a one-file helper, hardcoded fixture table, parser-only patch, pure unit-test gimmick, or shallow patch that bypasses the intended system path.
- Candidate setup should not require external credentials or live cloud services.

## Solution And Evaluator Contract

- `solution/` must contain a reference implementation that passes public and hidden tests.
- `evaluator/` must contain hidden tests that can run against the reference solution and a submitted candidate implementation.
- Hidden tests must use harder fixtures and stricter behavior than public tests.
- Hidden tests should defeat hardcoding, public-fixture-only solutions, overbroad retrieval/processing, shallow helper patches, and solutions that bypass the production path.
- Hidden evaluator material must never appear in rendered candidate main.

## Solution Public Parity

- The reference solution must pass the same public commands documented for the candidate repo, plus hidden evaluator tests.
- If the candidate README says `make test`, `make test-integration`, `make eval`, or `npm run test:public`, the reference solution must pass those same public behaviors or an explicitly equivalent rendered-solution command.
- Do not let solution-only tests drift away from candidate-facing behavior.
- The solution should prove that the public README contract is actually solvable.

## Local Production Simulator Rule

- Prefer a local production simulator over pure unit tests when the domain involves queues, storage, databases, vector search, workflows, traces, streaming, retries, or external APIs.
- Use Docker Compose for candidate-facing local services.
- Use local emulators and fakes instead of real credentials or cloud services.
- Add readiness retry logic inside application scripts, not fragile `sleep 10` waits in CI.
- Public tests may include fast unit tests, but at least one public integration path should use local services when service behavior is core to the challenge.
- Hidden/evaluator tests should add stricter service behavior, harder data, duplicate/retry/delay/restart cases, missing metadata, and ambiguity traps where relevant.

## Production Path Contract

- When a template claims to use a local service, at least one public or Docker-backed integration test must exercise that service through the same path the candidate is expected to fix.
- Do not count a service as part of the simulator if tests never touch it.
- A queue template must send and receive real messages through the local queue emulator.
- A vector-search template must index and query a real local vector database.
- A storage template must read and write through local object storage.
- A workflow template must execute the local workflow engine or faithful simulator.
- A Postgres-backed template must verify persisted state, not only in-memory state.
- A tracing template must emit or consume spans through the local trace path.

## Service Bypass Rule

- If the template includes a local service, public or hidden integration tests must fail if the candidate bypasses that service with hardcoded or in-memory-only behavior.
- The candidate must not be able to pass the meaningful integration gate by editing only a fake helper while ignoring the production path.
- Examples:
  - A queue challenge must verify messages actually flow through the local queue.
  - A vector-search challenge must verify the local vector DB is queried.
  - A storage challenge must verify documents are read from local object storage.
  - A tracing challenge must verify spans are emitted or consumed through the local trace path.
  - A streaming challenge must verify stream chunks, abort behavior, and persistence through the documented app path.

## Candidate Command Contract

Each candidate repo should expose a small, predictable command set. Use domain-specific names only when they are clearer.

Recommended Python-heavy pattern:

- `make dev`
- `make logs`
- `make seed`
- `make test`
- `make test-unit`
- `make test-integration`
- `make eval` or `make run`
- `make clean`

Recommended TypeScript-heavy pattern:

- `make dev`
- `make logs`
- `make seed`
- `make test`
- `make run`
- `make clean`

Commands must work from a fresh clone after dependency install.

## Candidate Time Budget

Every template must document:

- expected coding time
- expected setup time
- expected Docker image pull cost if services are heavy
- intended seniority level
- expected role fit

If setup takes more than 10 minutes on a normal laptop after images are cached, simplify the simulator or document why the heavier setup is justified.

## Expected Starter Failure Contract

- The starter should fail public validation for known, intentional reasons.
- Wrapper scripts must confirm the failure is expected, not random.
- Expected-failure wrappers should grep for stable markers such as `tenant_leak_detected`, `duplicate_deliveries`, `stale_doc_ranked_first`, `missing_grounded_citation`, `budget_exceeded_without_guard`, or `stream_abort_not_propagated`.
- Do not claim a template passes because the starter failed. It passes only when the wrapper confirms the intended failure.
- If the starter fails for a random infrastructure reason, import error, missing dependency, bad Docker readiness, or unrelated exception, the validation must fail.

## Root Validation Contract

Every golden template must expose these root commands through `Makefile`, `package.json`, or both:

- `validate-solution`
- `validate-candidate-main-expected-failure`
- `validate-docker-integration`
- `render`
- `scan-safety`
- `validate`

Expected behavior:

- `validate-solution`: reference solution passes public and hidden tests.
- `validate-candidate-main-expected-failure`: unsolved starter fails public unit/contract tests for expected markers.
- `validate-docker-integration`: Docker services start, seed/index/setup runs, public integration test runs, and the unsolved starter fails for expected markers.
- `render`: creates `generated/main` and `generated/solution`.
- `scan-safety`: fails if generated candidate main leaks private/internal material or secrets.
- `validate`: runs all required gates, including Docker-backed integration unless explicitly documented as unavailable.

## Render Contract

`tools/render_template.py` must create:

- `generated/main`
- `generated/solution`

`generated/main` may include only:

- `README.md`
- `DEBRIEF.md`
- local simulator files such as `docker-compose.yml`
- candidate commands such as `Makefile`
- candidate dependency manifests
- `src/`
- candidate simulators/fakes needed to run locally
- public fixtures
- public tests
- empty result directory placeholders

`generated/solution` may include:

- all candidate-safe material
- `solution/`
- `evaluator/`
- `SOLUTION.md`
- rubric
- hidden fixtures
- hidden tests
- expected outputs

## Rendered Repo Smoke Test

Validation must test the rendered outputs, not only the template source tree.

Required:

- `generated/main` installs or sets up successfully.
- `generated/main` expected-failure validation runs from inside the rendered candidate repo.
- `generated/solution` passes public and hidden validation or an equivalent evaluator target path.
- Safety scan runs against `generated/main`, not only `candidate/`.
- Rendered output must not rely on template-root-only paths unless those paths are intentionally included in the generated repo.

## Safety Scan Contract

`tools/scan_safety.py` must fail if `generated/main` contains:

- `solution/`
- `evaluator/`
- `tests_hidden/`
- `fixtures_hidden/`
- `SOLUTION.md` or `SOLUTION.md.j2`
- `rubric.md`
- private `expected/` outputs
- `source-dossiers/`
- `template.yaml`
- private keys
- `.env` files
- GitHub tokens
- AWS keys
- OpenAI keys
- Pinecone keys
- Supabase service role keys
- customer source paths
- real customer data markers

This is a lightweight local scan. Production release can still add Gitleaks or TruffleHog, but the template repo must have this baseline scan.

## Production Secret Scan

The local `scan_safety.py` is required for every template.

Before a template is used with customer-connected repos or source-slice mode, run at least one external secret scanner such as Gitleaks or TruffleHog against:

- the template repo
- `generated/main`
- `generated/solution`
- any approved source slice

This is not a replacement for `scan_safety.py`; it is an additional production gate.

## Metadata Contract

`template.yaml` must include:

- stable `id`
- title
- area/domain
- language or stack
- roles
- seniority
- time estimates
- local services
- no external credential rule
- evaluation axes
- source/repo matching signals
- candidate expected failures
- hidden-test strategy
- forbidden shortcut patterns

`metadata/source_mapping_rules.json` must help the template suggestion agent map recruiter repo signals to this template. Include:

- `template_id`
- positive signals
- negative signals
- stack matches
- best roles
- personalization knobs

`metadata/safety_policy.json` must state:

- no external credentials
- no cloud calls
- no startup source copying
- no real customer data
- candidate-main forbidden paths
- required scans
- allowed local services

## Source Dossier Contract

Each template needs a dossier under `source-dossiers/`.

The dossier must list:

- sources studied
- what architecture ideas are allowed to inspire the template
- what is forbidden

Allowed:

- architecture patterns
- generic benchmark structure
- public API concepts
- terminology
- metric names
- local emulator patterns

Forbidden:

- copying source code
- copying datasets wholesale
- copying complete exercises
- copying real customer code
- requiring live cloud services
- requiring credentials

## CI Contract

Remote GitHub Actions must run before a template is treated as a pattern for later templates.

CI should run:

- dependency install
- `validate-solution`
- `validate-candidate-main-expected-failure`
- `render`
- `scan-safety`
- `validate-docker-integration`
- Docker logs on failure

Do not call a template golden if remote CI has not passed.

## Failure Evidence Contract

CI must preserve enough evidence to debug failures.

On failure, CI should print or upload:

- Docker Compose logs
- public test output
- hidden test output
- generated safety scan report
- expected-failure wrapper output
- rendered repo tree when relevant

## Fresh-Clone Proof

Before final acceptance, run a fresh clone check:

- clone the pushed repo into `/tmp`
- verify important files have real line counts, especially `Makefile`, workflow YAML, Docker Compose, candidate Makefile, and `template.yaml`
- run the root validation command
- confirm no Docker containers are left running

If Docker image pulls are too slow or Docker validation cannot finish, say `not completed` and leave it as a blocker. Do not claim the integration path passes.

## GitHub Workflow

- Use the `trans-lucid` organization namespace.
- Create repos with `gh repo create trans-lucid/REPO_NAME --private --source=. --remote=origin --push` unless the user explicitly asks to keep it public during active work.
- If the repo already exists, do not recreate it. Use the existing remote, pull latest, and push scoped commits.
- Clone with `gh repo clone trans-lucid/REPO_NAME`.
- Fork into the org with `gh api repos/OWNER/REPO/forks -f organization='trans-lucid'`.
- Never fork into the personal account.
- Keep commits scoped and named around the template being created.

## Template Progress Tracking

Update `docs/template_progress.md` when a template moves stages:

- planned
- in progress
- golden-template-candidate
- golden

Include coverage areas, local services, validation status, remote CI status, and remaining cleanup notes.

## Source Repo Personalization Rule

When a recruiter connects a startup repo:

- Do not convert the startup repo into the challenge repo.
- Profile the startup repo for stack, domain, architecture, and role-relevant patterns.
- Match the repo to a template using `metadata/source_mapping_rules.json`.
- Personalize only safe parts of the generated challenge:
  - business nouns
  - scenario names
  - fixture field names
  - README context
  - stack/language selection
  - hidden-test emphasis
- Do not copy startup source unless explicit source-slice mode is approved.

## Source-Slice Mode Rule

Source-slice mode is disabled by default.

If explicitly approved:

- copy only the smallest safe slice needed for role realism
- never copy secrets, customer data, production configs, proprietary algorithms, or full service directories
- create `SOURCE_SLICE_MANIFEST.json`
- list every copied file, why it was copied, and how it was sanitized
- run `scan-safety`
- run at least one external secret scanner before publishing any generated repo

## Final Acceptance Checklist

Do not mark a template as a golden pattern until:

- solution passes public and hidden tests
- unsolved candidate fails public tests for known expected reasons
- Docker-backed public integration expected failure is validated locally and remotely
- render passes
- safety scan passes
- generated candidate main contains no hidden tests
- generated candidate main contains no `SOLUTION.md`
- generated candidate main contains no evaluator material
- generated candidate main contains no source dossier
- generated candidate main contains no private metadata
- source dossier is present
- source mapping rules are present
- safety policy is present
- remote GitHub Actions pass
- fresh-clone validation passes
- no lingering Docker containers remain after validation
- repo visibility is set correctly for the current phase
