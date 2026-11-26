"""Chain-of-Thought (CoT) Agent Package for Google ADK."""

from .agent import create_cot_agent, create_direct_agent, get_default_model, root_agent
from .prompts import (
    COT_SYSTEM_INSTRUCTION,
    DIRECT_SYSTEM_INSTRUCTION,
    FEW_SHOT_COT_EXEMPLARS,
    WORKFLOW_REASONER_INSTRUCTION,
    WORKFLOW_VERIFIER_INSTRUCTION,
    build_cot_instruction,
)
from .tools import calculate, calculate_tool
from .workflow import create_cot_workflow

__all__ = [
    "root_agent",
    "create_cot_agent",
    "create_direct_agent",
    "create_cot_workflow",
    "get_default_model",
    "COT_SYSTEM_INSTRUCTION",
    "DIRECT_SYSTEM_INSTRUCTION",
    "FEW_SHOT_COT_EXEMPLARS",
    "WORKFLOW_REASONER_INSTRUCTION",
    "WORKFLOW_VERIFIER_INSTRUCTION",
    "build_cot_instruction",
    "calculate",
    "calculate_tool",
]
