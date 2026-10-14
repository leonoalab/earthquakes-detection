import json
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.postgres import PostgresStore

from earthquake_rag.application.agent import build_agent
from earthquake_rag.application.memory_tools import build_memory_tools
from earthquake_rag.application.tools import build_earthquake_tools
from earthquake_rag.core.config import Settings
from earthquake_rag.domain.entities import AgentContext, AgentRun, ToolEvidence
from earthquake_rag.infrastructure.vector_store import KnowledgeStore


@contextmanager
def agent_runtime(settings: Settings) -> Iterator[Any]:
    settings.checkpoint_database_path.parent.mkdir(parents=True, exist_ok=True)
    knowledge = KnowledgeStore(settings.ai, settings.qdrant)
    try:
        tools = [*build_earthquake_tools(knowledge), *build_memory_tools()]
        with PostgresStore.from_conn_string(settings.memory_store_url) as store:
            store.setup()
            with SqliteSaver.from_conn_string(
                str(settings.checkpoint_database_path)
            ) as checkpointer:
                checkpointer.setup()
                yield build_agent(settings.ai, tools, checkpointer, store)
    finally:
        knowledge.close()


def invoke_agent(
    settings: Settings,
    *,
    question: str,
    thread_id: str,
    context: AgentContext,
) -> AgentRun:
    with agent_runtime(settings) as graph:
        result = graph.invoke(
            {"messages": [{"role": "user", "content": question}]},
            config={"configurable": {"thread_id": thread_id}},
            context=context,
        )
    messages = result["messages"]
    return AgentRun(
        answer=_content_to_text(messages[-1].content),
        tools=_extract_evidence(messages),
        message_count=len(messages),
    )


def render_agent_graph(settings: Settings) -> str:
    with agent_runtime(settings) as graph:
        return graph.get_graph().draw_mermaid()


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False, default=str)


def _extract_evidence(messages: list[Any]) -> list[ToolEvidence]:
    calls: dict[str, ToolEvidence] = {}
    for message in messages:
        if isinstance(message, AIMessage):
            for call in message.tool_calls:
                call_id = str(call.get("id", ""))
                calls[call_id] = ToolEvidence(
                    name=str(call.get("name", "unknown")),
                    arguments=dict(call.get("args") or {}),
                )
        elif isinstance(message, ToolMessage):
            call_id = str(message.tool_call_id)
            evidence = calls.setdefault(
                call_id,
                ToolEvidence(name=message.name or "unknown", arguments={}),
            )
            evidence.output = _content_to_text(message.content)
    return list(calls.values())
