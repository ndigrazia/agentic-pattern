"""Unit tests for ADK Web compatibility and application discovery."""

import importlib
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.adk.agents import BaseAgent, LlmAgent


def test_cot_agent_package_exports_root_agent():
    """Verify cot_agent package exposes a valid root_agent required by adk web."""
    mod = importlib.import_module("cot_agent")
    assert hasattr(mod, "root_agent"), "cot_agent package must export 'root_agent'"

    agent = getattr(mod, "root_agent")
    assert isinstance(agent, BaseAgent), f"Expected BaseAgent, got {type(agent)}"
    assert agent.name == "cot_agent"


def test_cot_agent_properties():
    """Verify root_agent has description, calculator tool, and CoT instruction."""
    from cot_agent.agent import root_agent

    assert isinstance(root_agent, LlmAgent)
    assert "Chain-of-Thought" in root_agent.description
    assert len(root_agent.tools) == 1
    assert root_agent.tools[0].name == "calculate"
    assert "### 1. Problem Decomposition & Premises" in root_agent.instruction
    assert "### 2. Step-by-Step Chain of Thought" in root_agent.instruction
    assert "### 3. Verification & Sanity Check" in root_agent.instruction
    assert "### 4. Final Answer" in root_agent.instruction
