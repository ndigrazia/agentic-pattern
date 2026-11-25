import os
from pathlib import Path
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import (
    AGENT_CARD_WELL_KNOWN_PATH,
    RemoteA2aAgent,
)
from registry import A2AAgentRegistry

load_dotenv()

PORT = int(os.getenv("ADK_PORT", "8000"))
DEFAULT_MATH_A2A_URL = f"http://localhost:{PORT}/a2a/math_agent{AGENT_CARD_WELL_KNOWN_PATH}"

# Resolve math_agent URL from registry if available, else fallback to default
registry = A2AAgentRegistry()
entry = registry.get("math_agent")
if entry and entry.get("url"):
    reg_url = entry["url"]
    A2A_MATH_AGENT_CARD_URL = (
        reg_url if reg_url.endswith(".json") else f"{reg_url.rstrip('/')}{AGENT_CARD_WELL_KNOWN_PATH}"
    )
else:
    A2A_MATH_AGENT_CARD_URL = os.getenv("A2A_MATH_AGENT_URL", DEFAULT_MATH_A2A_URL)

# Remote A2A Agent representing the standalone/specialist math agent
math_remote_agent = RemoteA2aAgent(
    name="math_agent",
    description="Specialized math and computation agent. Delegates any arithmetic, mathematical calculation, multiplication, power, or factorial to this agent.",
    agent_card=A2A_MATH_AGENT_CARD_URL,
)


MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-3.8-flash")

root_agent = Agent(
    name="coordinator_agent",
    model=MODEL_NAME,
    description="Primary Coordinator Assistant that interacts with users in ADK Web and delegates mathematical computations to the specialized math agent via A2A protocol.",
    instruction="""
    You are the Primary Coordinator Agent for users in the ADK Web UI.
    - Greet users and answer general knowledge or conversational questions directly using your own capabilities.
    - When the user asks any mathematical question, calculation, arithmetic (addition, multiplication, powers, factorials, etc.):
      1. Delegate the task to `math_agent`.
      2. Do not attempt to compute mathematical equations yourself; rely on `math_agent`.
      3. Present the answer returned by `math_agent` clearly and politely to the user.
    """,
    sub_agents=[math_remote_agent],
)
