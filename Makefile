.PHONY: install infra-up infra-down infra-status db-init sync events ingestions

RUN=uv run --env-file .env

install:
	uv sync

infra-up:
	docker compose up -d postgres qdrant

infra-down:
	docker compose down

infra-status:
	docker compose ps

db-init:
	$(RUN) earthquake-rag init-db

sync:
	$(RUN) earthquake-rag sync

HOURS?=24
events:
	$(RUN) earthquake-rag events --hours $(HOURS)

ingestions:
	$(RUN) earthquake-rag ingestions
