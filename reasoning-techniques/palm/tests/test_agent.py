"""Unit tests for PALM Agent configuration, tool bindings, and structure."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.adk.agents import Agent
from google.adk.code_executors import BaseCodeExecutor, BuiltInCodeExecutor
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.google_search_tool import GoogleSearchTool

from palm_agent import coding_agent, create_palm_system, root_agent, search_agent


def test_search_agent_structure():
    """Verify SearchAgent configuration and google_search tool."""
    assert search_agent.name == "SearchAgent"
    assert "Google Search" in search_agent.instruction
    assert len(search_agent.tools) == 1
    assert any(isinstance(t, GoogleSearchTool) or "GoogleSearch" in str(type(t)) for t in search_agent.tools)


def test_coding_agent_structure():
    """Verify CodeAgent configuration and BuiltInCodeExecutor."""
    assert coding_agent.name == "CodeAgent"
    assert "Code Execution" in coding_agent.instruction
    assert coding_agent.code_executor is not None
    assert isinstance(coding_agent.code_executor, BaseCodeExecutor)


def test_root_agent_structure():
    """Verify RootAgent has both AgentTool instances for SearchAgent and CodeAgent."""
    assert root_agent.name == "RootAgent"
    assert root_agent.description == "Root Agent"
    assert len(root_agent.tools) == 2

    tool_names = [t.name for t in root_agent.tools]
    assert "SearchAgent" in tool_names
    assert "CodeAgent" in tool_names

    for t in root_agent.tools:
        assert isinstance(t, AgentTool)


def test_code_executor_list_tolerance():
    """Ensure Agent tolerates code_executor=[BuiltInCodeExecutor] without Pydantic errors."""
    test_agent = Agent(
        model="gemini-2.0-flash",
        name="TolerantAgent",
        instruction="Test",
        code_executor=[BuiltInCodeExecutor],
    )
    assert isinstance(test_agent.code_executor, BaseCodeExecutor)


def test_create_palm_system_factory():
    """Verify create_palm_system creates a valid configured RootAgent."""
    custom_root = create_palm_system(model_name="gemini-2.5-flash")
    assert custom_root.name == "RootAgent"
    assert len(custom_root.tools) == 2
    tool_names = [t.name for t in custom_root.tools]
    assert "SearchAgent" in tool_names
    assert "CodeAgent" in tool_names
