# Earthquake RAG

A temporal and agentic RAG application built with real USGS earthquake data,
PostgreSQL, Qdrant, Ollama, LangChain, LangGraph, LangSmith and Streamlit.

The complete Spanish tutorial is maintained in the separate `tutorial` branch.

## Quick start

```bash
cp .env.example .env
uv sync
docker compose up -d
```

For optional tracing, configure `LANGSMITH_TRACING`, `LANGSMITH_API_KEY` and
`LANGSMITH_PROJECT`. Do not combine a classic project with
`LANGSMITH_AGENT_ID` or `LANGSMITH_AGENT_ENVIRONMENT`.
