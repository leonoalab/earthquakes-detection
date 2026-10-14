# Earthquake RAG

A temporal and agentic RAG application built with real USGS earthquake data.
It combines PostgreSQL, Qdrant, Ollama, LangChain, LangGraph, optional
LangSmith tracing and a Streamlit interface.

The complete Spanish tutorial is maintained in the separate `tutorial` branch.
The `main` branch contains only the application, while each tutorial milestone
is available as an annotated `step-*` tag.

## Requirements

- Python 3.12 and `uv`
- Docker with Compose
- Ollama running locally

```bash
ollama pull qwen3:8b
ollama pull embeddinggemma
```

## Run the application

```bash
cp .env.example .env
uv sync
make bootstrap
make ui
```

Open Streamlit at `http://localhost:8501` and the Qdrant dashboard at
`http://localhost:6333/dashboard`.

## Useful commands

```bash
make sync
make index
make search Q="What is the difference between magnitude and intensity?"
make ask Q="Why do aftershocks occur?"
make agent Q="What was the strongest earthquake in the last 24 hours, and what does its magnitude mean?"
make graph
make studio
```

`make studio` starts the local Agent Server at `http://127.0.0.1:2024`.
Open `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`
to inspect the explicit `START`/`END` workflow, conditional routes and tool loop.

## Optional LangSmith tracing

Configure a classic project in `.env`:

```dotenv
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_your_key
LANGSMITH_PROJECT=earthquake-rag-local
```

Do not combine these variables with `LANGSMITH_AGENT_ID` or
`LANGSMITH_AGENT_ENVIRONMENT`. The Makefile removes inherited agent-address
variables before starting the application.
