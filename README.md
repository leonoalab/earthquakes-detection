# Earthquake RAG

Read the complete step-by-step tutorial in Spanish:

[Los datos cambian: así construí un RAG temporal con información real de terremotos](https://rocky-azimuth-fcc.notion.site/Los-datos-cambian-as-constru-un-RAG-temporal-con-informaci-n-real-de-terremotos-3cecb657b19080bc9cc9ca7db3861790)

and in English:
[Data Changes: How I Built a Time-Aware RAG with Real Earthquake Data](https://rocky-azimuth-fcc.notion.site/Data-Changes-How-I-Built-a-Time-Aware-RAG-with-Real-Earthquake-Data-3facb657b1908006a520de47ad13e893?pvs=73)

Each project milestone is available as an annotated `step-*` Git tag.

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
