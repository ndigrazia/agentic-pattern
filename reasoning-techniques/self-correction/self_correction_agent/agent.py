"""Agent definition and factory for Self-Correction Reasoning with Google ADK."""

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
        SELF_CORRECTION_SYSTEM_INSTRUCTION,
        WORKFLOW_GENERATOR_INSTRUCTION,
        build_self_correction_instruction,
    )
    from .tools import (
        analyze_text_metrics_tool,
        verify_constraint_checklist_tool,
    )
except ImportError:
    from prompts import (
        SELF_CORRECTION_SYSTEM_INSTRUCTION,
        WORKFLOW_GENERATOR_INSTRUCTION,
        build_self_correction_instruction,
    )
    from tools import (
        analyze_text_metrics_tool,
        verify_constraint_checklist_tool,
    )

load_dotenv()


def get_default_model() -> str:
    """Retrieves default Gemini model name from environment or fallback."""
    return os.getenv("GEMINI_MODEL_NAME", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))


def create_self_correction_agent(
    model_name: Optional[str] = None,
    mode: str = "few-shot",
    enable_tools: bool = True,
    name: str = "self_correction_agent",
) -> LlmAgent:
    """Creates an ADK LlmAgent configured for systematic self-correction.

    Args:
        model_name: Foundation model name (defaults to GEMINI_MODEL_NAME env var).
        mode: Reasoning mode ('few-shot' or 'zero-shot').
        enable_tools: Whether to attach text metrics and constraint verification tools.
        name: Name for the agent (used by ADK Web UI discovery).

    Returns:
        Configured LlmAgent instance.
    """
    model = model_name or get_default_model()
    instruction = build_self_correction_instruction(mode=mode, enable_tools=enable_tools)
    tools = [analyze_text_metrics_tool, verify_constraint_checklist_tool] if enable_tools else []

    return LlmAgent(
        name=name,
        model=model,
        instruction=instruction,
        description=(
            "Self-Correction Agent. Reviews generated content against original requirements "
            "using a 5-step systematic process: Understand Requirements, Analyze Content, "
            "Identify Weaknesses, Propose Improvements, and Generate Revised Content."
        ),
        tools=tools,
    )


def create_draft_agent(
    model_name: Optional[str] = None,
    name: str = "draft_writer",
) -> LlmAgent:
    """Creates an initial content generator agent for multi-stage pipelines.

    Args:
        model_name: Foundation model name.
        name: Name for the draft agent.

    Returns:
        Configured LlmAgent instance.
    """
    model = model_name or get_default_model()
    return LlmAgent(
        name=name,
        model=model,
        instruction=WORKFLOW_GENERATOR_INSTRUCTION,
        description="Generates initial draft content based on prompt and requirements.",
        tools=[],
    )


# Root agent discovered and served by Google ADK Web UI
root_agent = create_self_correction_agent(mode="few-shot", enable_tools=True)
