"""Tests for ADK Web compatibility and application discovery."""

import importlib
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.adk.agents import BaseAgent
from google.genai import types


def test_optimization_agent_package_exports_root_agent():
    """Verify optimization_agent exposes a valid root_agent required by adk web."""
    mod = importlib.import_module("optimization_agent")
    assert hasattr(mod, "root_agent"), "optimization_agent package must export 'root_agent'"

    agent = getattr(mod, "root_agent")
    assert isinstance(agent, BaseAgent), f"Expected BaseAgent, got {type(agent)}"
    assert agent.name == "optimization_agent"
    assert len(agent.sub_agents) == 2
    sub_names = [sub.name for sub in agent.sub_agents]
    assert "GeminiFlashAgent" in sub_names
    assert "GeminiProAgent" in sub_names


def test_adk_agent_definition_properties():
    """Verify optimization_agent has description and complexity threshold configured."""
    from optimization_agent.agent import root_agent

    assert "Resource-Aware" in root_agent.description
    assert root_agent.complexity_threshold == 0.5
    assert hasattr(root_agent, "flash_agent")
    assert hasattr(root_agent, "pro_agent")
