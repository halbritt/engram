PYTHON := .venv/bin/python
DATABASE_URL ?= postgresql:///engram
TEST_DATABASE_URL ?= postgresql:///engram_test
DOCKER_DATABASE_URL ?= postgresql://engram:engram@127.0.0.1:54329/engram
DOCKER_TEST_DATABASE_URL ?= postgresql://engram:engram@127.0.0.1:54329/engram_test
EXPORT_PATH := $(if $(filter command line,$(origin PATH)),$(PATH),)

.PHONY: install db-up db-down wait-db migrate migrate-docker ingest-chatgpt ingest-chatgpt-docker ingest-claude ingest-claude-docker ingest-gemini ingest-gemini-docker segment segment-docker embed embed-docker pipeline pipeline-docker test test-db test-docker test-db-docker schema-docs

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

ingest-chatgpt: install
	@if [ -z "$(EXPORT_PATH)" ]; then echo "Usage: make ingest-chatgpt PATH=/path/to/chatgpt-export"; exit 2; fi
	ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli ingest-chatgpt "$(EXPORT_PATH)"

ingest-chatgpt-docker: install wait-db
	@if [ -z "$(EXPORT_PATH)" ]; then echo "Usage: make ingest-chatgpt-docker PATH=/path/to/chatgpt-export"; exit 2; fi
	ENGRAM_DATABASE_URL="$(DOCKER_DATABASE_URL)" $(PYTHON) -m engram.cli ingest-chatgpt "$(EXPORT_PATH)"

ingest-claude: install
	@if [ -z "$(EXPORT_PATH)" ]; then echo "Usage: make ingest-claude PATH=/path/to/claude-export"; exit 2; fi
	ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli ingest-claude "$(EXPORT_PATH)"

ingest-claude-docker: install wait-db
	@if [ -z "$(EXPORT_PATH)" ]; then echo "Usage: make ingest-claude-docker PATH=/path/to/claude-export"; exit 2; fi
	ENGRAM_DATABASE_URL="$(DOCKER_DATABASE_URL)" $(PYTHON) -m engram.cli ingest-claude "$(EXPORT_PATH)"

ingest-gemini: install
	@if [ -z "$(EXPORT_PATH)" ]; then echo "Usage: make ingest-gemini PATH=/path/to/google-takeout"; exit 2; fi
	ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli ingest-gemini "$(EXPORT_PATH)"

ingest-gemini-docker: install wait-db
	@if [ -z "$(EXPORT_PATH)" ]; then echo "Usage: make ingest-gemini-docker PATH=/path/to/google-takeout"; exit 2; fi
	ENGRAM_DATABASE_URL="$(DOCKER_DATABASE_URL)" $(PYTHON) -m engram.cli ingest-gemini "$(EXPORT_PATH)"

segment: install
	ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli segment

segment-docker: install wait-db
	ENGRAM_DATABASE_URL="$(DOCKER_DATABASE_URL)" $(PYTHON) -m engram.cli segment

embed: install
	ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli embed

embed-docker: install wait-db
	ENGRAM_DATABASE_URL="$(DOCKER_DATABASE_URL)" $(PYTHON) -m engram.cli embed

pipeline: install
	ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) -m engram.cli pipeline

pipeline-docker: install wait-db
	ENGRAM_DATABASE_URL="$(DOCKER_DATABASE_URL)" $(PYTHON) -m engram.cli pipeline

test-db:
	@createdb engram_test 2>/dev/null || true

test-db-docker: wait-db
	@docker compose exec -T db psql -U engram -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'engram_test'" | grep -q 1 || docker compose exec -T db createdb -U engram engram_test

test: install test-db
	ENGRAM_TEST_DATABASE_URL="$(TEST_DATABASE_URL)" $(PYTHON) -m pytest

test-docker: install test-db-docker
	ENGRAM_TEST_DATABASE_URL="$(DOCKER_TEST_DATABASE_URL)" $(PYTHON) -m pytest

schema-docs: install
	ENGRAM_DATABASE_URL="$(DATABASE_URL)" $(PYTHON) scripts/gen_schema_docs.py
