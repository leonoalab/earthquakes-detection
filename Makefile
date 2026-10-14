.PHONY: install infra-up infra-down infra-status

RUN=uv run --env-file .env

install:
	uv sync

infra-up:
	docker compose up -d postgres qdrant

infra-down:
	docker compose down

infra-status:
	docker compose ps
