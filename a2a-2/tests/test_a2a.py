import json
from pathlib import Path
from coordinator_agent.agent import root_agent as coordinator_root
from math_agent.agent import (
    root_agent as math_root,
    add,
    multiply,
    power,
    factorial,
)
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent


def test_math_tools():
    assert add(10, 5) == 15
    assert multiply(6, 7) == 42
    assert power(2, 3) == 8
    assert factorial(5) == 120


def test_math_agent_structure():
    assert math_root.name == "math_agent"
    tool_names = [t.__name__ if hasattr(t, "__name__") else str(t) for t in math_root.tools]
    assert "add" in tool_names
    assert "multiply" in tool_names
    assert "power" in tool_names
    assert "factorial" in tool_names


def test_coordinator_agent_structure():
    assert coordinator_root.name == "coordinator_agent"
    assert len(coordinator_root.sub_agents) >= 1
    remote_agent = coordinator_root.sub_agents[0]
    assert isinstance(remote_agent, RemoteA2aAgent)
    assert remote_agent.name == "math_agent"


def test_math_agent_card_json():
    agent_json_path = Path(__file__).resolve().parent.parent / "math_agent" / "agent.json"
    assert agent_json_path.exists()
    with open(agent_json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["name"] == "math_agent"
    assert "skills" in data
    assert len(data["skills"]) >= 1
    assert "tags" in data["skills"][0]
def test_registry_operations(tmp_path):
    from registry import A2AAgentRegistry

    reg_file = tmp_path / "test_reg.json"
    registry = A2AAgentRegistry(registry_file=reg_file)

    # 1. Register from dict
    card = {
        "name": "test_agent",
        "description": "A test agent",
        "url": "http://localhost:8000/a2a/test_agent",
        "skills": [{"id": "test_skill", "name": "Testing", "tags": ["test", "demo"]}],
    }
    registry.register(card_data=card)
    assert registry.get("test_agent") is not None
    assert len(registry.list_agents()) == 1

    # 2. Search
    found = registry.search("demo")
    assert len(found) == 1
    assert found[0]["name"] == "test_agent"

    # 3. Create remote agent
    remote = registry.create_remote_agent("test_agent")
    assert isinstance(remote, RemoteA2aAgent)
    assert remote.name == "test_agent"

    # 4. Unregister
    assert registry.unregister("test_agent") is True
    assert registry.get("test_agent") is None
    assert len(registry.list_agents()) == 0

