import re
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime
from langgraph.store.base import BaseStore

from earthquake_rag.application.agent import build_contextual_prompt
from earthquake_rag.application.memory_tools import (
    memory_tool_completed,
    requested_memory_tool,
)
from earthquake_rag.core.config import AISettings
from earthquake_rag.domain.entities import AgentContext

MAX_TOOL_ROUNDS = 3
MAX_VALIDATION_ATTEMPTS = 2


class ResearchState(MessagesState):
    """State persisted by LangGraph between nodes and conversation turns."""

    route: Literal["research", "conversation"]
    tool_rounds: int
    validation_attempts: int
    evidence_found: bool
    retry_instruction: str | None
    stop_reason: str | None


def _latest_user_text(state: ResearchState) -> str:
    for message in reversed(state["messages"]):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


def _is_conversation_only(text: str) -> bool:
    normalized = re.sub(r"[^a-záéíóúñ ]", "", text.lower()).strip()
    return normalized in {
        "hello",
        "hi",
        "hola",
        "thanks",
        "thank you",
        "gracias",
        "help",
        "ayuda",
        "what can you do",
        "qué puedes hacer",
        "que puedes hacer",
    }


def _has_current_turn_evidence(state: ResearchState) -> bool:
    for message in reversed(state["messages"]):
        if isinstance(message, ToolMessage):
            return True
        if isinstance(message, HumanMessage):
            return False
    return False


def build_research_workflow(
    ai: AISettings,
    tools: list[BaseTool],
    checkpointer: BaseCheckpointSaver | None = None,
    store: BaseStore | None = None,
):
    """Build an explicit, inspectable LangGraph workflow around the tools."""
    model = ChatOllama(
        model=ai.chat_model,
        base_url=ai.ollama_base_url,
        temperature=0,
    )
    research_model = model.bind_tools(tools)

    def classify_request(state: ResearchState) -> dict:
        route = (
            "conversation"
            if _is_conversation_only(_latest_user_text(state))
            else "research"
        )
        return {
            "route": route,
            "tool_rounds": 0,
            "validation_attempts": 0,
            "evidence_found": False,
            "retry_instruction": None,
            "stop_reason": None,
        }

    def route_request(
        state: ResearchState,
    ) -> Literal["conversation_model", "research_model"]:
        return (
            "conversation_model"
            if state["route"] == "conversation"
            else "research_model"
        )

    def prompt_for(state: ResearchState, runtime: Runtime[AgentContext]) -> str:
        context = runtime.context or AgentContext()
        prompt = build_contextual_prompt(context, runtime.store)
        if state.get("retry_instruction"):
            prompt = f"{prompt}\n\n{state['retry_instruction']}"
        return prompt

    def conversation_model(
        state: ResearchState,
        runtime: Runtime[AgentContext],
    ) -> dict:
        prompt = prompt_for(state, runtime)
        response = model.invoke(
            [
                SystemMessage(
                    content=(
                        f"{prompt}\n\nThis is a conversational request. Briefly explain "
                        "the assistant's scope without claiming to have researched data."
                    )
                ),
                *state["messages"],
            ]
        )
        return {"messages": [response], "stop_reason": "conversation"}

    def call_research_model(
        state: ResearchState,
        runtime: Runtime[AgentContext],
    ) -> dict:
        active_model = research_model
        memory_tool_name = requested_memory_tool(state["messages"])
        if memory_tool_name and not memory_tool_completed(
            state["messages"], memory_tool_name
        ):
            selected_tools = [tool for tool in tools if tool.name == memory_tool_name]
            if selected_tools:
                active_model = model.bind_tools(
                    selected_tools,
                    tool_choice="required",
                )

        response = active_model.invoke(
            [SystemMessage(content=prompt_for(state, runtime)), *state["messages"]]
        )
        return {"messages": [response]}

    def route_after_model(
        state: ResearchState,
    ) -> Literal["execute_tools", "validate_evidence", "limit_reached"]:
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            if state["tool_rounds"] >= MAX_TOOL_ROUNDS:
                return "limit_reached"
            return "execute_tools"
        return "validate_evidence"

    def record_evidence(state: ResearchState) -> dict:
        return {
            "tool_rounds": state["tool_rounds"] + 1,
            "evidence_found": _has_current_turn_evidence(state),
            "retry_instruction": None,
        }

    def validate_evidence(state: ResearchState) -> dict:
        return {
            "evidence_found": _has_current_turn_evidence(state),
            "validation_attempts": state["validation_attempts"] + 1,
        }

    def route_after_validation(
        state: ResearchState,
    ) -> Literal["finish", "retry_with_grounding", "fallback"]:
        if state["evidence_found"]:
            return "finish"
        if state["validation_attempts"] < MAX_VALIDATION_ATTEMPTS:
            return "retry_with_grounding"
        return "fallback"

    def retry_with_grounding(_: ResearchState) -> dict:
        return {
            "retry_instruction": (
                "The previous draft was not grounded in tool evidence. You must call "
                "at least one relevant tool before answering. Do not repeat the draft."
            )
        }

    def finish(_: ResearchState) -> dict:
        return {"stop_reason": "grounded_answer"}

    def fallback(_: ResearchState) -> dict:
        return {
            "messages": [
                AIMessage(
                    content=(
                        "I could not verify this answer with the available tools after "
                        "two attempts, so I will not present an ungrounded result."
                    )
                )
            ],
            "stop_reason": "missing_evidence",
        }

    def limit_reached(state: ResearchState) -> dict:
        last_message = state["messages"][-1]
        skipped_results: list[ToolMessage] = []
        if isinstance(last_message, AIMessage):
            skipped_results = [
                ToolMessage(
                    content="Skipped because the workflow reached its tool-round limit.",
                    tool_call_id=str(call["id"]),
                    name=str(call["name"]),
                )
                for call in last_message.tool_calls
            ]
        return {
            "messages": [
                *skipped_results,
                AIMessage(
                    content=(
                        "I stopped after three tool rounds to avoid an uncontrolled "
                        "loop. The available evidence was not enough for a final answer."
                    )
                ),
            ],
            "stop_reason": "tool_round_limit",
        }

    builder = StateGraph(ResearchState, context_schema=AgentContext)
    builder.add_node("classify_request", classify_request)
    builder.add_node("conversation_model", conversation_model)
    builder.add_node("research_model", call_research_model)
    builder.add_node("execute_tools", ToolNode(tools))
    builder.add_node("record_evidence", record_evidence)
    builder.add_node("validate_evidence", validate_evidence)
    builder.add_node("retry_with_grounding", retry_with_grounding)
    builder.add_node("finish", finish)
    builder.add_node("fallback", fallback)
    builder.add_node("limit_reached", limit_reached)

    builder.add_edge(START, "classify_request")
    builder.add_conditional_edges("classify_request", route_request)
    builder.add_edge("conversation_model", END)
    builder.add_conditional_edges("research_model", route_after_model)
    builder.add_edge("execute_tools", "record_evidence")
    builder.add_edge("record_evidence", "research_model")
    builder.add_conditional_edges("validate_evidence", route_after_validation)
    builder.add_edge("retry_with_grounding", "research_model")
    builder.add_edge("finish", END)
    builder.add_edge("fallback", END)
    builder.add_edge("limit_reached", END)

    return builder.compile(
        checkpointer=checkpointer,
        store=store,
        name="earthquake_research_workflow",
    )
