import json
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, ToolMessage
from langchain_ollama import ChatOllama

from earthquake_rag.application.tools import build_earthquake_tools
from earthquake_rag.core.config import Settings
from earthquake_rag.domain.entities import AgentRun, ToolEvidence
from earthquake_rag.infrastructure.vector_store import KnowledgeStore

SYSTEM_PROMPT = """
You are an educational earthquake research assistant.

Use the available tools whenever the question requires stored USGS data or
information from the educational documents.

Grounding contract:
- Every factual statement in the final answer must be supported by tool output.
- If the question contains a conceptual part, call search_earthquake_knowledge
  before answering that part. Otherwise, say that it was not researched.
- Never add hazard classifications, damage scenarios, shaking distances or
  safety conclusions that are absent from tool output.

Rules:
- Never invent earthquake events, values, dates, statistics or links.
- Use calculate_earthquake_statistics for counts and aggregates.
- Use search_earthquake_knowledge for conceptual explanations.
- For a mixed factual and conceptual question, use both data and knowledge tools.
- Separate USGS data, deterministic calculations and educational interpretation.
- Cite the source filenames returned by the knowledge tool.
- Cite local source filenames as plain text, never as invented hyperlinks.
- Include the USGS URL when discussing a specific event.
- Do not call every magnitude value a Richter-scale measurement.
- A tsunami flag is not proof that an active warning exists.
- Never claim that a tsunami occurred from `tsunami_processing_flag=true`.
- Never translate a PAGER colour into "safe" or "no danger".
- Do not infer safety or damage from magnitude, depth or alert colour alone.
- Use only links returned by tools.
- Do not add numerical examples or calculations not present in tool evidence.
- If evidence is unavailable, state the limitation clearly.
""".strip()


class EarthquakeAgent:
    def __init__(self, settings: Settings) -> None:
        self.knowledge = KnowledgeStore(settings.ai, settings.qdrant)
        model = ChatOllama(
            model=settings.ai.chat_model,
            base_url=settings.ai.ollama_base_url,
            temperature=0,
        )
        self.graph = create_agent(
            model=model,
            tools=build_earthquake_tools(self.knowledge),
            system_prompt=SYSTEM_PROMPT,
        )

    def ask(self, question: str) -> AgentRun:
        result = self.graph.invoke(
            {"messages": [{"role": "user", "content": question}]}
        )
        messages = result["messages"]
        return AgentRun(
            answer=self._content_to_text(messages[-1].content),
            tools=self._extract_evidence(messages),
            message_count=len(messages),
        )

    def mermaid(self) -> str:
        return self.graph.get_graph().draw_mermaid()

    def close(self) -> None:
        self.knowledge.close()

    @staticmethod
    def _content_to_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        return json.dumps(content, ensure_ascii=False, default=str)

    @classmethod
    def _extract_evidence(cls, messages: list[Any]) -> list[ToolEvidence]:
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
                evidence.output = cls._content_to_text(message.content)
        return list(calls.values())
