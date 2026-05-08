PYTHON := .venv/bin/python
DATABASE_URL ?= postgresql:///engram
TEST_DATABASE_URL ?= postgresql:///engram_test
DOCKER_DATABASE_URL ?= postgresql://engram:engram@127.0.0.1:54329/engram
DOCKER_TEST_DATABASE_URL ?= postgresql://engram:engram@127.0.0.1:54329/engram_test
EXPORT_PATH := $(if $(filter command line,$(origin PATH)),$(PATH),)
SEGMENTER_MODEL ?=
SEGMENTER_MODEL_ENV := $(if $(SEGMENTER_MODEL),ENGRAM_SEGMENTER_MODEL="$(SEGMENTER_MODEL)",)
STRIATUM_REPO ?= $(HOME)/git/striatum

.PHONY: install db-up db-down wait-db migrate migrate-docker phase1-ingest-chatgpt phase1-ingest-chatgpt-docker phase1-ingest-claude phase1-ingest-claude-docker phase1-ingest-gemini phase1-ingest-gemini-docker ingest-chatgpt ingest-chatgpt-docker ingest-claude ingest-claude-docker ingest-gemini ingest-gemini-docker phase2-segment phase2-segment-docker phase2-embed phase2-embed-docker phase2-run phase2-run-docker phase2-run-isolated segment segment-docker segment-isolated pipeline-isolated embed embed-docker extract extract-docker consolidate consolidate-docker pipeline pipeline-docker pipeline-3 pipeline-3-docker phase3-extract phase3-extract-docker phase3-consolidate phase3-consolidate-docker phase3-run phase3-run-docker phase3-interview-start phase3-interview-resume phase3-interview-history phase3-interview-export phase3-interview-list-sessions phase3-interview-coverage phase3-interview-enable-active-learning phase4-refresh phase4-build-entities phase4-smoke phase4-smoke-docker test test-db test-docker test-db-docker schema-docs check-refs lint format typecheck install-striatum striatum-init phase4-validate phase4-prepare phase4-status phase4-gate-validate phase4-gate-prepare phase4-gate-status phase4-gate-dashboard rfc25-validate rfc25-prepare rfc25-status rfc25-impl-validate rfc25-impl-prepare rfc25-impl-status

install: .venv/.installed

.venv/.installed: pyproject.toml
	/usr/bin/python3 -m venv .venv
	$(PYTHON) -m pip install -e ".[dev]"
	/usr/bin/touch .venv/.installed

db-up:
	docker compose up -d db

db-down:
	docker compose down

wait-db: db-up
	@for i in $$(seq 1 30); do \
		if docker compose exec -T db pg_isready -U engram -d postgres >/dev/null 2>&1; then exit 0; fi; \
		sleep 1; \
	done; \
	echo "Postgres did not become ready in time"; exit 1

migrate: install
	ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli migrate

migrate-docker: install wait-db
	ENGRAM_DATABASE_URL="$(DOCKER_DATABASE_URL)" $(PYTHON) -m engram.cli migrate

phase1-ingest-chatgpt: install
	@if [ -z "$(EXPORT_PATH)" ]; then echo "Usage: make phase1-ingest-chatgpt PATH=/path/to/chatgpt-export"; exit 2; fi
	ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli phase1 ingest-chatgpt "$(EXPORT_PATH)"

phase1-ingest-chatgpt-docker: install wait-db
	@if [ -z "$(EXPORT_PATH)" ]; then echo "Usage: make phase1-ingest-chatgpt-docker PATH=/path/to/chatgpt-export"; exit 2; fi
	ENGRAM_DATABASE_URL="$(DOCKER_DATABASE_URL)" $(PYTHON) -m engram.cli phase1 ingest-chatgpt "$(EXPORT_PATH)"

phase1-ingest-claude: install
	@if [ -z "$(EXPORT_PATH)" ]; then echo "Usage: make phase1-ingest-claude PATH=/path/to/claude-export"; exit 2; fi
	ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli phase1 ingest-claude "$(EXPORT_PATH)"

phase1-ingest-claude-docker: install wait-db
	@if [ -z "$(EXPORT_PATH)" ]; then echo "Usage: make phase1-ingest-claude-docker PATH=/path/to/claude-export"; exit 2; fi
	ENGRAM_DATABASE_URL="$(DOCKER_DATABASE_URL)" $(PYTHON) -m engram.cli phase1 ingest-claude "$(EXPORT_PATH)"

phase1-ingest-gemini: install
	@if [ -z "$(EXPORT_PATH)" ]; then echo "Usage: make phase1-ingest-gemini PATH=/path/to/google-takeout"; exit 2; fi
	ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli phase1 ingest-gemini "$(EXPORT_PATH)"

phase1-ingest-gemini-docker: install wait-db
	@if [ -z "$(EXPORT_PATH)" ]; then echo "Usage: make phase1-ingest-gemini-docker PATH=/path/to/google-takeout"; exit 2; fi
	ENGRAM_DATABASE_URL="$(DOCKER_DATABASE_URL)" $(PYTHON) -m engram.cli phase1 ingest-gemini "$(EXPORT_PATH)"

ingest-chatgpt:
	@echo "warning: make ingest-chatgpt is deprecated; use make phase1-ingest-chatgpt" >&2
	@$(MAKE) phase1-ingest-chatgpt PATH="$(EXPORT_PATH)"

ingest-chatgpt-docker:
	@echo "warning: make ingest-chatgpt-docker is deprecated; use make phase1-ingest-chatgpt-docker" >&2
	@$(MAKE) phase1-ingest-chatgpt-docker PATH="$(EXPORT_PATH)"

ingest-claude:
	@echo "warning: make ingest-claude is deprecated; use make phase1-ingest-claude" >&2
	@$(MAKE) phase1-ingest-claude PATH="$(EXPORT_PATH)"

ingest-claude-docker:
	@echo "warning: make ingest-claude-docker is deprecated; use make phase1-ingest-claude-docker" >&2
	@$(MAKE) phase1-ingest-claude-docker PATH="$(EXPORT_PATH)"

ingest-gemini:
	@echo "warning: make ingest-gemini is deprecated; use make phase1-ingest-gemini" >&2
	@$(MAKE) phase1-ingest-gemini PATH="$(EXPORT_PATH)"

ingest-gemini-docker:
	@echo "warning: make ingest-gemini-docker is deprecated; use make phase1-ingest-gemini-docker" >&2
	@$(MAKE) phase1-ingest-gemini-docker PATH="$(EXPORT_PATH)"

phase2-segment: install
	$(SEGMENTER_MODEL_ENV) ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli phase2 segment $(if $(LIMIT),--limit $(LIMIT),)

phase2-segment-docker: install wait-db
	$(SEGMENTER_MODEL_ENV) ENGRAM_DATABASE_URL="$(DOCKER_DATABASE_URL)" $(PYTHON) -m engram.cli phase2 segment $(if $(LIMIT),--limit $(LIMIT),)

phase2-embed: install
	ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli phase2 embed $(if $(LIMIT),--limit $(LIMIT),)

phase2-embed-docker: install wait-db
	ENGRAM_DATABASE_URL="$(DOCKER_DATABASE_URL)" $(PYTHON) -m engram.cli phase2 embed $(if $(LIMIT),--limit $(LIMIT),)

phase2-run: install
	$(SEGMENTER_MODEL_ENV) ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli phase2 run $(if $(LIMIT),--limit $(LIMIT),)

phase2-run-docker: install wait-db
	$(SEGMENTER_MODEL_ENV) ENGRAM_DATABASE_URL="$(DOCKER_DATABASE_URL)" $(PYTHON) -m engram.cli phase2 run $(if $(LIMIT),--limit $(LIMIT),)

segment:
	@echo "warning: make segment is deprecated; use make phase2-segment" >&2
	@$(MAKE) phase2-segment

segment-docker:
	@echo "warning: make segment-docker is deprecated; use make phase2-segment-docker" >&2
	@$(MAKE) phase2-segment-docker

embed:
	@echo "warning: make embed is deprecated; use make phase2-embed" >&2
	@$(MAKE) phase2-embed

embed-docker:
	@echo "warning: make embed-docker is deprecated; use make phase2-embed-docker" >&2
	@$(MAKE) phase2-embed-docker

pipeline:
	@printf '%s\n' "ambiguous target: pipeline" "Use one of:" "  make phase2-run" "  make phase2-run-docker" "  make phase2-run-isolated" "  make phase3-run" "  make phase4-smoke" >&2
	@exit 2

pipeline-docker:
	@printf '%s\n' "ambiguous target: pipeline-docker" "Use one of:" "  make phase2-run-docker" "  make phase3-run-docker" "  make phase4-smoke-docker" >&2
	@exit 2

phase3-extract: install
	$(SEGMENTER_MODEL_ENV) ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli phase3 extract $(if $(LIMIT),--limit $(LIMIT),)

phase3-extract-docker: install wait-db
	$(SEGMENTER_MODEL_ENV) ENGRAM_DATABASE_URL="$(DOCKER_DATABASE_URL)" $(PYTHON) -m engram.cli phase3 extract $(if $(LIMIT),--limit $(LIMIT),)

phase3-consolidate: install
	ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli phase3 consolidate $(if $(LIMIT),--limit $(LIMIT),)

phase3-consolidate-docker: install wait-db
	ENGRAM_DATABASE_URL="$(DOCKER_DATABASE_URL)" $(PYTHON) -m engram.cli phase3 consolidate $(if $(LIMIT),--limit $(LIMIT),)

phase3-run: install
	$(SEGMENTER_MODEL_ENV) ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli phase3 run $(if $(LIMIT),--limit $(LIMIT),)

phase3-run-docker: install wait-db
	$(SEGMENTER_MODEL_ENV) ENGRAM_DATABASE_URL="$(DOCKER_DATABASE_URL)" $(PYTHON) -m engram.cli phase3 run $(if $(LIMIT),--limit $(LIMIT),)

phase3-interview-start: install
	ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli phase3 interview start $(if $(N),--n $(N),) $(if $(SEED),--seed $(SEED),)

phase3-interview-resume: install
	ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli phase3 interview resume $(if $(SESSION_ID),--session-id $(SESSION_ID),)

phase3-interview-history: install
	ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli phase3 interview history $(if $(TARGET),--target $(TARGET),)

phase3-interview-export: install
	ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli phase3 interview export $(if $(TIER_MAX),--privacy-tier-max $(TIER_MAX),)

phase3-interview-list-sessions: install
	ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli phase3 interview list-sessions

phase3-interview-coverage: install
	ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli phase3 interview coverage --strata "$(STRATA)"

phase3-interview-enable-active-learning: install
	ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli phase3 interview enable-active-learning --signal-version "$(SIGNAL_VERSION)"

extract:
	@echo "warning: make extract is deprecated; use make phase3-extract" >&2
	@$(MAKE) phase3-extract

extract-docker:
	@echo "warning: make extract-docker is deprecated; use make phase3-extract-docker" >&2
	@$(MAKE) phase3-extract-docker

consolidate:
	@echo "warning: make consolidate is deprecated; use make phase3-consolidate" >&2
	@$(MAKE) phase3-consolidate

consolidate-docker:
	@echo "warning: make consolidate-docker is deprecated; use make phase3-consolidate-docker" >&2
	@$(MAKE) phase3-consolidate-docker

pipeline-3:
	@echo "warning: make pipeline-3 is deprecated; use make phase3-run" >&2
	@$(MAKE) phase3-run

pipeline-3-docker:
	@echo "warning: make pipeline-3-docker is deprecated; use make phase3-run-docker" >&2
	@$(MAKE) phase3-run-docker

phase4-refresh: install
	ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli phase4 refresh-current-beliefs

phase4-build-entities: install
	ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli phase4 build-entities $(if $(LIMIT),--limit $(LIMIT),)

phase4-smoke: install
	ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli phase4 smoke --limit $(or $(LIMIT),25)

phase4-smoke-docker: install wait-db
	ENGRAM_DATABASE_URL="$(DOCKER_DATABASE_URL)" $(PYTHON) -m engram.cli phase4 smoke --limit $(or $(LIMIT),25)

# segment-isolated and pipeline-isolated stop openclaw-gateway and ik-llama-watchdog.timer
# for the duration of the run, then restore them. The watchdog calls /health, which blocks
# while a slot is occupied — under load it false-positives and SIGTERMs ik-llama mid-generation
# (see docs/reviews/v1/PHASE_2_CODE_REVIEW_FINDINGS.md, Empirical Findings I).
ENGRAM_QUIESCED_UNITS := openclaw-gateway.service ik-llama-watchdog.timer

segment-isolated: install
	@echo "warning: make segment-isolated is deprecated; use make phase2-segment" >&2
	@trap 'for u in $(ENGRAM_QUIESCED_UNITS); do systemctl --user start $$u 2>/dev/null || true; done' EXIT INT TERM; \
	for u in $(ENGRAM_QUIESCED_UNITS); do systemctl --user stop $$u 2>/dev/null || true; done; \
	$(SEGMENTER_MODEL_ENV) ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli phase2 segment $(if $(LIMIT),--limit $(LIMIT),)

phase2-run-isolated: install
	@trap 'for u in $(ENGRAM_QUIESCED_UNITS); do systemctl --user start $$u 2>/dev/null || true; done' EXIT INT TERM; \
	for u in $(ENGRAM_QUIESCED_UNITS); do systemctl --user stop $$u 2>/dev/null || true; done; \
	$(SEGMENTER_MODEL_ENV) ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli phase2 run $(if $(LIMIT),--limit $(LIMIT),)

pipeline-isolated:
	@printf '%s\n' "ambiguous target: pipeline-isolated" "Use one of:" "  make phase2-run-isolated" "  make phase2-run" "  make phase3-run" "  make phase4-smoke" >&2
	@exit 2

test-db:
	@createdb engram_test 2>/dev/null || true

test-db-docker: wait-db
	@docker compose exec -T db psql -U engram -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'engram_test'" | grep -q 1 || docker compose exec -T db createdb -U engram engram_test

test: install test-db
	ENGRAM_TEST_DATABASE_URL="$(TEST_DATABASE_URL)" $(PYTHON) -m pytest

test-docker: install test-db-docker
	ENGRAM_TEST_DATABASE_URL="$(DOCKER_TEST_DATABASE_URL)" $(PYTHON) -m pytest

check-refs:
	python3 scripts/check_artifact_refs.py --root .

STRIATUM := .venv/bin/striatum

install-striatum: install
	$(PYTHON) -m pip install -e "$(STRIATUM_REPO)"

striatum-init: install-striatum
	$(STRIATUM) --repo . init

phase4-validate: install-striatum
	$(STRIATUM) --repo . workflow validate striatum/phase-4-spec-review/workflow.json

phase4-prepare: install-striatum
	$(STRIATUM) --repo . run prepare --workflow striatum/phase-4-spec-review/workflow.json

phase4-status: install-striatum
	$(STRIATUM) --repo . status

phase4-gate-validate: install-striatum
	$(STRIATUM) --repo . workflow validate striatum/phase-4-tiered-gate/workflow.json

phase4-gate-prepare: install-striatum
	$(STRIATUM) --repo . run prepare --workflow striatum/phase-4-tiered-gate/workflow.json

phase4-gate-status: install-striatum
	$(STRIATUM) --repo . status

phase4-gate-dashboard: install-striatum
	$(STRIATUM) --repo . dashboard

rfc25-validate: install-striatum
	$(STRIATUM) --repo . workflow validate striatum/rfc-0025-command-names-review/workflow.json

rfc25-prepare: install-striatum
	$(STRIATUM) --repo . run prepare --workflow striatum/rfc-0025-command-names-review/workflow.json

rfc25-status: install-striatum
	$(STRIATUM) --repo . status

rfc25-impl-validate: install-striatum
	$(STRIATUM) --repo . workflow validate striatum/rfc-0025-command-surface-implementation/workflow.json

rfc25-impl-prepare: install-striatum
	$(STRIATUM) --repo . run prepare --workflow striatum/rfc-0025-command-surface-implementation/workflow.json

rfc25-impl-status: install-striatum
	$(STRIATUM) --repo . status

lint: install
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

format: install
	$(PYTHON) -m ruff format .

typecheck: install
	$(PYTHON) -m pyright src tests

schema-docs: install
	ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) scripts/gen_schema_docs.py
