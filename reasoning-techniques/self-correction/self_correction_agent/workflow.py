"""Two-stage Self-Correction Workflow (DraftWriter -> SelfCorrectionCritic) using Google ADK."""

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
        WORKFLOW_GENERATOR_INSTRUCTION,
        WORKFLOW_CRITIC_INSTRUCTION,
    )
    from .tools import (
        analyze_text_metrics_tool,
        verify_constraint_checklist_tool,
    )
except ImportError:
    from prompts import (
        WORKFLOW_GENERATOR_INSTRUCTION,
        WORKFLOW_CRITIC_INSTRUCTION,
    )
    from tools import (
        analyze_text_metrics_tool,
        verify_constraint_checklist_tool,
    )

load_dotenv()


def get_default_model() -> str:
    return os.getenv("GEMINI_MODEL_NAME", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))


def create_self_correction_workflow(
    model_name: Optional[str] = None,
    name: str = "self_correction_pipeline",
) -> Workflow:
    """Builds a two-stage Self-Correction pipeline.

    Stage 1: DraftWriter Agent generates an initial draft addressing the user prompt,
             saving the initial text to session.state["draft_content"].
    Stage 2: SelfCorrectionCritic Agent reviews the initial draft against the original requirements,
             executing the 5-step systematic self-correction process (Thought 1-5),
             verifying constraints with metrics tools, and producing the final revised content.

    Args:
        model_name: Foundation model name to use across agents.
        name: Name for the workflow.

    Returns:
        ADK Workflow orchestrating DraftWriter and SelfCorrectionCritic sequentially.
    """
    model = model_name or get_default_model()

    # Stage 1: Generate initial draft
    generator_agent = LlmAgent(
        name="DraftWriter",
        model=model,
        instruction=WORKFLOW_GENERATOR_INSTRUCTION,
        description="Generates the first unrefined draft from prompt specifications.",
        output_key="draft_content",
    )

    # Stage 2: Systematic Self-Correction and Polish
    critic_agent = LlmAgent(
        name="SelfCorrectionCritic",
        model=model,
        instruction=WORKFLOW_CRITIC_INSTRUCTION,
        description="Critiques draft against requirements via 5-step CoT and outputs polished revision.",
        output_key="corrected_content",
        tools=[analyze_text_metrics_tool, verify_constraint_checklist_tool],
    )

    pipeline = Workflow(
        name=name,
        edges=[
            (START, generator_agent),
            (generator_agent, critic_agent),
        ],
        description="Two-stage Self-Correction workflow: DraftWriter creates draft, SelfCorrectionCritic refines it.",
    )

    return pipeline
