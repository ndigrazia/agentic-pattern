"""Program-Aided Language Models (PALM / PAL) Agent Package for Google ADK."""

from .agent import (
    coding_agent,
    create_palm_system,
    get_default_model,
    root_agent,
    search_agent,
)
from .prompts import (
    CODE_AGENT_INSTRUCTION,
    PALM_ROOT_INSTRUCTION,
    SEARCH_AGENT_INSTRUCTION,
)

__all__ = [
    "root_agent",
    "search_agent",
    "coding_agent",
    "create_palm_system",
    "get_default_model",
    "SEARCH_AGENT_INSTRUCTION",
    "CODE_AGENT_INSTRUCTION",
    "PALM_ROOT_INSTRUCTION",
]
