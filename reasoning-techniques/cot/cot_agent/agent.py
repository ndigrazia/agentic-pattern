"""Agent definition and factory for Chain-of-Thought (CoT) reasoning with Google ADK."""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Optional

# Ensure package directory is in sys.path
package_dir = str(Path(__file__).resolve().parent)
parent_dir = str(Path(__file__).resolve().parent.parent)
for p in (package_dir, parent_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

from dotenv import load_dotenv
from google.adk.agents import LlmAgent

try:
    from .prompts import (
        COT_SYSTEM_INSTRUCTION,
        DIRECT_SYSTEM_INSTRUCTION,
        build_cot_instruction,
    )
    from .tools import calculate_tool
except ImportError:
    from prompts import (
        COT_SYSTEM_INSTRUCTION,
        DIRECT_SYSTEM_INSTRUCTION,
        build_cot_instruction,
    )
    from tools import calculate_tool

load_dotenv()


def get_default_model() -> str:
    """Retrieves default Gemini model name from environment or fallback."""
    return os.getenv("GEMINI_MODEL_NAME", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))


def create_cot_agent(
    model_name: Optional[str] = None,
    mode: str = "zero-shot",
    enable_tools: bool = True,
    name: str = "cot_agent",
) -> LlmAgent:
    """Creates an ADK LlmAgent configured with Chain-of-Thought reasoning.

    Args:
        model_name: Foundation model name (defaults to GEMINI_MODEL_NAME env var).
        mode: Reasoning mode ('zero-shot' or 'few-shot').
        enable_tools: Whether to attach arithmetic and calculation tools.
        name: Name for the agent.

    Returns:
        Configured LlmAgent instance.
    """
    model = model_name or get_default_model()
    instruction = build_cot_instruction(mode=mode, enable_tools=enable_tools)
    tools = [calculate_tool] if enable_tools else []

    return LlmAgent(
        name=name,
        model=model,
        instruction=instruction,
        description=(
            "Chain-of-Thought (CoT) Reasoning Agent. Explicitly breaks down problems "
            "into decomposed premises, sequential deduction steps, sanity checks, "
            "and final synthesized answers."
        ),
        tools=tools,
    )


def create_direct_agent(
    model_name: Optional[str] = None,
    name: str = "direct_agent",
) -> LlmAgent:
    """Creates a baseline agent without CoT instructions for comparison.

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
        description="Standard Direct Agent that responds immediately without explicit scratchpad reasoning.",
        tools=[],
    )


# Root agent discovered and served by Google ADK Web UI
root_agent = create_cot_agent(mode="zero-shot", enable_tools=True)
