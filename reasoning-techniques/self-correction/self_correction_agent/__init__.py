"""Self-Correction Reasoning Technique Package for Google ADK."""

from .agent import (
    create_draft_agent,
    create_self_correction_agent,
    get_default_model,
    root_agent,
)
from .prompts import (
    SELF_CORRECTION_EXEMPLARS,
    SELF_CORRECTION_SYSTEM_INSTRUCTION,
    WORKFLOW_CRITIC_INSTRUCTION,
    WORKFLOW_GENERATOR_INSTRUCTION,
    build_self_correction_instruction,
)
from .tools import (
    analyze_text_metrics,
    analyze_text_metrics_tool,
    verify_constraint_checklist,
    verify_constraint_checklist_tool,
)
from .workflow import create_self_correction_workflow

__all__ = [
    "root_agent",
    "create_self_correction_agent",
    "create_draft_agent",
    "create_self_correction_workflow",
    "get_default_model",
    "SELF_CORRECTION_SYSTEM_INSTRUCTION",
    "SELF_CORRECTION_EXEMPLARS",
    "WORKFLOW_GENERATOR_INSTRUCTION",
    "WORKFLOW_CRITIC_INSTRUCTION",
    "build_self_correction_instruction",
    "analyze_text_metrics",
    "analyze_text_metrics_tool",
    "verify_constraint_checklist",
    "verify_constraint_checklist_tool",
]
