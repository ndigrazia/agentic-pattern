"""Reasoning and Acting (ReAct) Agent Package for Google ADK."""

from .agent import create_direct_agent, create_react_agent, get_default_model, root_agent
from .prompts import (
    DIRECT_SYSTEM_INSTRUCTION,
    FEW_SHOT_REACT_EXEMPLARS,
    REACT_SYSTEM_INSTRUCTION,
    build_react_instruction,
)
from .tools import (
    ALL_REACT_TOOLS,
    calculator,
    calculator_tool,
    database_lookup,
    database_tool,
    metrics_tool,
    search_knowledge_base,
    search_tool,
    system_metrics_query,
)

__all__ = [
    "root_agent",
    "create_react_agent",
    "create_direct_agent",
    "get_default_model",
    "REACT_SYSTEM_INSTRUCTION",
    "DIRECT_SYSTEM_INSTRUCTION",
    "FEW_SHOT_REACT_EXEMPLARS",
    "build_react_instruction",
    "calculator",
    "calculator_tool",
    "search_knowledge_base",
    "search_tool",
    "system_metrics_query",
    "metrics_tool",
    "database_lookup",
    "database_tool",
    "ALL_REACT_TOOLS",
]
