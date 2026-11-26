"""Two-stage Chain-of-Thought Workflow (Reasoner -> Verifier) using Google ADK."""

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
from google.adk.workflow import Workflow, START

try:
    from .prompts import (
        WORKFLOW_REASONER_INSTRUCTION,
        WORKFLOW_VERIFIER_INSTRUCTION,
    )
    from .tools import calculate_tool
except ImportError:
    from prompts import (
        WORKFLOW_REASONER_INSTRUCTION,
        WORKFLOW_VERIFIER_INSTRUCTION,
    )
    from tools import calculate_tool

load_dotenv()


def get_default_model() -> str:
    return os.getenv("GEMINI_MODEL_NAME", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))


def create_cot_workflow(
    model_name: Optional[str] = None,
    name: str = "cot_workflow_pipeline",
) -> Workflow:
    """Builds a two-stage Chain-of-Thought pipeline.

    Stage 1: CoTReasoner Agent breaks down the problem and documents intermediate reasoning steps,
             saving the full thought chain to session.state["reasoning_chain"].
    Stage 2: CoTVerifier Agent audits each step of the reasoning chain for logical gaps,
             arithmetic errors, and constraint compliance, outputting the verified answer.

    Args:
        model_name: Foundation model name to use across agents.
        name: Name for the workflow.

    Returns:
        ADK Workflow orchestrating the Reasoner and Verifier sequentially.
    """
    model = model_name or get_default_model()

    # Stage 1: Problem Decomposition and Step-by-Step Chain of Thought
    reasoner_agent = LlmAgent(
        name="CoTReasoner",
        model=model,
        instruction=WORKFLOW_REASONER_INSTRUCTION,
        description="Deconstructs user queries and produces transparent step-by-step reasoning chains.",
        output_key="reasoning_chain",
        tools=[calculate_tool],
    )

    # Stage 2: Independent verification and synthesis of the final solution
    verifier_agent = LlmAgent(
        name="CoTVerifier",
        model=model,
        instruction=WORKFLOW_VERIFIER_INSTRUCTION,
        description="Audits the thought chain for logical/numerical errors and issues the certified final answer.",
        output_key="verified_answer",
    )

    pipeline = Workflow(
        name=name,
        edges=[
            (START, reasoner_agent),
            (reasoner_agent, verifier_agent),
        ],
        description="Two-stage Chain-of-Thought workflow: Reasoner generates steps, Verifier audits and certifies.",
    )

    return pipeline
