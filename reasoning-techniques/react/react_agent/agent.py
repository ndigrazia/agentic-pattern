"""Agent definition and factory for Reasoning and Acting (ReAct) with Google ADK."""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Optional

# Ensure package and parent directory are in sys.path for direct imports
package_dir = str(Path(__file__).resolve().parent)
parent_dir = str(Path(__file__).resolve().parent.parent)
for p in (package_dir, parent_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

from dotenv import load_dotenv
from google.adk.agents import LlmAgent

try:
    from .prompts import (
        DIRECT_SYSTEM_INSTRUCTION,
        REACT_SYSTEM_INSTRUCTION,
        build_react_instruction,
    )
    from .tools import ALL_REACT_TOOLS
except ImportError:
    from prompts import (
        DIRECT_SYSTEM_INSTRUCTION,
        REACT_SYSTEM_INSTRUCTION,
        build_react_instruction,
    )
    from tools import ALL_REACT_TOOLS

load_dotenv()


def get_default_model() -> str:
    """Retrieves default Gemini model name from environment or fallback."""
    return os.getenv("GEMINI_MODEL_NAME", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))


def create_react_agent(
    model_name: Optional[str] = None,
    mode: str = "few-shot",
    enable_tools: bool = True,
    name: str = "react_agent",
) -> LlmAgent:
    """Creates a Google ADK LlmAgent configured with the ReAct reasoning-acting loop.

    Args:
        model_name: Foundation model name (defaults to GEMINI_MODEL_NAME env var).
        mode: ReAct mode ('few-shot' with exemplars or 'zero-shot').
        enable_tools: Whether to attach knowledge search, calculator, metrics, and database tools.
        name: Name for the agent (used by ADK Web UI discovery and routing).

    Returns:
        Configured LlmAgent instance.
    """
    model = model_name or get_default_model()
    instruction = build_react_instruction(mode=mode, enable_tools=enable_tools)
    tools = list(ALL_REACT_TOOLS) if enable_tools else []

    return LlmAgent(
        name=name,
        model=model,
        instruction=instruction,
        description=(
            "ReAct (Reasoning and Acting) Agent. Interleaves dynamic reasoning traces (Thought) "
            "with targeted tool calls (Action) and environment feedback (Observation) "
            "to reliably solve multi-step knowledge retrieval, telemetry, and computational problems."
        ),
        tools=tools,
    )


def create_direct_agent(
    model_name: Optional[str] = None,
    name: str = "direct_agent",
) -> LlmAgent:
    """Creates a baseline agent without ReAct instructions or external tools for comparison.

    Args:
        model_name: Foundation model name.
        name: Name for the baseline agent.

    Returns:
        Configured LlmAgent instance.
    """
    model = model_name or get_default_model()
    return LlmAgent(
        name=name,
        model=model,
        instruction=DIRECT_SYSTEM_INSTRUCTION,
        description="Standard Direct Agent that responds immediately from internal parametric memory without tools.",
        tools=[],
    )


# Root agent discovered and served by Google ADK Web UI (adk web)
root_agent = create_react_agent(mode="few-shot", enable_tools=True)
