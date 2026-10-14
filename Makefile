.PHONY: install infra-up infra-down infra-status db-init sync events ingestions \
	index search ask tools agent graph

RUN=env -u LANGSMITH_AGENT_ID -u LANGSMITH_AGENT_ENVIRONMENT \
	-u LANGCHAIN_PROJECT -u LANGCHAIN_SESSION uv run --env-file .env

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

index:
	$(RUN) earthquake-rag index

Q?=What is the difference between magnitude and intensity?
search:
	$(RUN) earthquake-rag search "$(Q)"

ask:
	$(RUN) earthquake-rag ask "$(Q)"

tools:
	$(RUN) earthquake-rag tools

THREAD?=tutorial-1
USER_ID?=student-1
agent:
	$(RUN) earthquake-rag agent "$(Q)" \
		--thread-id "$(THREAD)" --user-id "$(USER_ID)"

graph:
	$(RUN) earthquake-rag graph
