"""Unit and integration tests for ADK Web compatibility and application discovery."""

import importlib
from pathlib import Path
import sys
import pytest

base_dir = str(Path(__file__).resolve().parent.parent)
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from fastapi.testclient import TestClient
from google.adk.agents import BaseAgent, LlmAgent
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.cli.utils.agent_loader import AgentLoader


def test_react_agent_package_exports_root_agent():
    """Verify react_agent package exposes a valid root_agent required by adk web."""
    mod = importlib.import_module("react_agent")
    assert hasattr(mod, "root_agent"), "react_agent package must export 'root_agent'"

    agent = getattr(mod, "root_agent")
    assert isinstance(agent, BaseAgent), f"Expected BaseAgent, got {type(agent)}"
    assert agent.name == "react_agent"


def test_root_agent_properties():
    """Verify root_agent has description, tools, and ReAct loop instruction."""
    from react_agent.agent import root_agent

    assert isinstance(root_agent, LlmAgent)
    assert "ReAct" in root_agent.description
    assert len(root_agent.tools) == 4

    tool_names = {t.name for t in root_agent.tools}
    assert "search_knowledge_base" in tool_names
    assert "calculator" in tool_names
    assert "system_metrics_query" in tool_names
    assert "database_lookup" in tool_names

    assert "Thought:" in root_agent.instruction
    assert "Action:" in root_agent.instruction
    assert "Observation:" in root_agent.instruction
    assert "Final Answer:" in root_agent.instruction


def test_adk_agent_loader_discovery():
    """Verify AgentLoader finds 'react_agent' as a discovered application in this folder."""
    loader = AgentLoader(base_dir)
    agents = loader.list_agents()
    assert "react_agent" in agents

    details = loader.list_agents_detailed()
    match = next((a for a in details if a["name"] == "react_agent"), None)
    assert match is not None
    assert match["root_agent_name"] == "react_agent"
    assert "ReAct" in match["description"]

    loaded = loader.load_agent("react_agent")
    assert isinstance(loaded, BaseAgent)
    assert loaded.name == "react_agent"


def test_adk_web_fastapi_endpoints():
    """Verify ADK Web FastAPI application exposes endpoints and lists react_agent."""
    app = get_fast_api_app(
        agents_dir=base_dir,
        web=True,
        use_local_storage=False,
        session_service_uri="memory://",
    )
    client = TestClient(app)

    # 1. Test /list-apps
    res_list = client.get("/list-apps")
    assert res_list.status_code == 200
    assert "react_agent" in res_list.json()

    # 2. Test /apps/react_agent/app-info
    res_info = client.get("/apps/react_agent/app-info")
    assert res_info.status_code == 200
    data = res_info.json()
    assert data["name"] == "react_agent"
    assert data["rootAgentName"] == "react_agent"
    assert len(data["agents"]["react_agent"]["tools"]) == 4

    # 3. Test Web root page /
    res_root = client.get("/")
    assert res_root.status_code == 200
