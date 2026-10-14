import json
from collections.abc import Sequence
from typing import Literal

from langchain.tools import ToolRuntime, tool
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool

from earthquake_rag.domain.entities import AgentContext

PREFERENCES_KEY = "learning_preferences"
SAVE_PREFERENCES_TOOL = "save_learning_preferences"
CLEAR_PREFERENCES_TOOL = "clear_learning_preferences"

_SAVE_MEMORY_MARKERS = (
    "remember",
    "recuerda",
    "memoriza",
    "guarda mi preferencia",
    "guarda que",
    "i prefer",
    "my preference",
    "prefiero",
    "mi preferencia",
)
_CLEAR_MEMORY_MARKERS = (
    "forget",
    "olvida",
    "borra mi preferencia",
    "borra mis preferencias",
    "elimina mi preferencia",
    "elimina mis preferencias",
    "clear my preference",
    "delete my preference",
)


def preferences_namespace(user_id: str) -> tuple[str, ...]:
    return ("users", user_id)


def requested_memory_tool(messages: Sequence[BaseMessage]) -> str | None:
    """Return the memory tool explicitly requested in the latest user turn."""
    for message in reversed(messages):
        if not isinstance(message, HumanMessage):
            continue
        text = _message_text(message).lower()
        if any(marker in text for marker in _CLEAR_MEMORY_MARKERS):
            return CLEAR_PREFERENCES_TOOL
        if any(marker in text for marker in _SAVE_MEMORY_MARKERS):
            return SAVE_PREFERENCES_TOOL
        return None
    return None


def memory_tool_completed(
    messages: Sequence[BaseMessage], tool_name: str
) -> bool:
    """Check whether a memory tool has completed in the latest user turn."""
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return False
        if isinstance(message, ToolMessage) and message.name == tool_name:
            return True
    return False


def _message_text(message: HumanMessage) -> str:
    if isinstance(message.content, str):
        return message.content
    return json.dumps(message.content, ensure_ascii=False, default=str)


def build_memory_tools() -> list[BaseTool]:
    @tool
    def save_learning_preferences(
        detail_level: Literal["brief", "balanced", "detailed"],
        use_examples: bool,
        interests: list[str],
        runtime: ToolRuntime[AgentContext],
    ) -> str:
        """Persist learning preferences explicitly stated by the current user.

        Call this tool whenever the user asks you to remember a preference or
        states how future explanations should be written. Never claim that a
        preference was saved until this tool returns successfully. Never infer
        or store preferences that the user did not express.
        """
        if runtime.store is None:
            return "Long-term memory is unavailable."
        value = {
            "detail_level": detail_level,
            "use_examples": use_examples,
            "interests": interests,
        }
        runtime.store.put(
            preferences_namespace(runtime.context.user_id),
            PREFERENCES_KEY,
            value,
        )
        return f"Learning preferences saved: {json.dumps(value)}"

    @tool
    def clear_learning_preferences(runtime: ToolRuntime[AgentContext]) -> str:
        """Delete the current user's saved learning preferences.

        Call this only when the user explicitly asks you to forget or remove
        their preferences. Never claim deletion until this tool succeeds.
        """
        if runtime.store is None:
            return "Long-term memory is unavailable."
        runtime.store.delete(
            preferences_namespace(runtime.context.user_id), PREFERENCES_KEY
        )
        return "Learning preferences deleted."

    return [save_learning_preferences, clear_learning_preferences]
