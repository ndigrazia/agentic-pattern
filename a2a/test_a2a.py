import pytest
from adk_agent import create_agent
from google.adk.agents import LlmAgent
from a2a.types import AgentCard, AgentSkill, AgentCapabilities


def test_create_agent():
    agent = create_agent(client_id="test_id", client_secret="test_secret")
    assert isinstance(agent, LlmAgent)
    assert agent.name == "calendar_agent"


def test_agent_card_structure():
    skill = AgentSkill(
        id="check_availability",
        name="Check Availability",
        description="Checks a user's availability for a time using their Google Calendar",
        tags=["calendar"],
        examples=["Am I free from 10am to 11am tomorrow?"],
    )
    agent_card = AgentCard(
        name="Calendar Agent",
        description="An agent that can manage a user's calendar",
        url="http://localhost:10007/",
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
    )
    data = agent_card.model_dump()
    assert data["name"] == "Calendar Agent"
    assert data["capabilities"]["streaming"] is True
    assert len(data["skills"]) == 1
    assert data["skills"][0]["id"] == "check_availability"
