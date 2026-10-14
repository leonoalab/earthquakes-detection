"""Graph export used by the local LangGraph Agent Server and Studio."""

from earthquake_rag.application.memory_tools import build_memory_tools
from earthquake_rag.application.tools import build_earthquake_tools
from earthquake_rag.application.workflow import build_research_workflow
from earthquake_rag.core.config import get_settings
from earthquake_rag.infrastructure.vector_store import KnowledgeStore

settings = get_settings()
knowledge = KnowledgeStore(settings.ai, settings.qdrant)
tools = [*build_earthquake_tools(knowledge), *build_memory_tools()]

# Agent Server supplies persistence when it loads this compiled graph.
graph = build_research_workflow(settings.ai, tools)
