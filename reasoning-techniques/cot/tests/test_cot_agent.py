"""Unit tests for the Chain-of-Thought (CoT) Agent and prompt configuration."""

import asyncio
from pathlib import Path
import sys
from typing import AsyncGenerator
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.adk.agents import BaseAgent, InvocationContext, LlmAgent
from google.adk.events import Event
from google.adk.runners import InMemoryRunner
from google.genai import types

from cot_agent import (
    COT_SYSTEM_INSTRUCTION,
    DIRECT_SYSTEM_INSTRUCTION,
    FEW_SHOT_COT_EXEMPLARS,
    build_cot_instruction,
    create_cot_agent,
    create_direct_agent,
    get_default_model,
)


class MockReasoningAgent(BaseAgent):
    """Deterministic mock agent simulating CoT reasoning."""
    name: str = "cot_agent"
    response_text: str = (
        "### 1. Problem Decomposition & Premises\n"
        "- Initial stock: 100\n\n"
        "### 2. Step-by-Step Chain of Thought\n"
        "- Step 1: Sold 20 => Remaining = 80\n"
        "- Step 2: Added 10 => Remaining = 90\n\n"
        "### 3. Verification & Sanity Check\n"
        "- Verified 100 - 20 + 10 = 90.\n\n"
        "### 4. Final Answer\n"
        "90 items remain."
    )

    async def _run_async_impl(
        self, context: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=self.response_text)],
            ),
        )


def test_cot_agent_initialization_defaults():
    agent = create_cot_agent()
    assert isinstance(agent, LlmAgent)
    assert agent.name == "cot_agent"
    assert "Chain-of-Thought" in agent.description
    assert len(agent.tools) == 1
    assert agent.tools[0].name == "calculate"
    assert "Problem Decomposition & Premises" in agent.instruction
    assert "Step-by-Step Chain of Thought" in agent.instruction
    assert "Verification & Sanity Check" in agent.instruction
    assert "Final Answer" in agent.instruction


def test_cot_agent_few_shot_mode():
    agent = create_cot_agent(mode="few-shot")
    assert "Few-Shot Demonstrations" in agent.instruction
    assert "Multi-Step Mathematical & Rate Problem" in agent.instruction
    assert "Deductive Logic & Constraint Satisfaction" in agent.instruction


def test_cot_agent_custom_model_and_tools_toggle():
    agent = create_cot_agent(model_name="custom-model-x", enable_tools=False)
    assert agent.model == "custom-model-x"
    assert len(agent.tools) == 0


def test_direct_agent_baseline():
    direct = create_direct_agent(model_name="direct-model")
    assert direct.model == "direct-model"
    assert direct.name == "direct_agent"
    assert "without showing intermediate thinking steps" in direct.instruction
    assert len(direct.tools) == 0


def test_mock_runner_execution():
    async def _run():
        agent = MockReasoningAgent()
        runner = InMemoryRunner(agent)
        user_id = "test_user"
        session_id = "test_sess"

        await runner.session_service.create_session(
            app_name=runner.app_name, user_id=user_id, session_id=session_id
        )

        msg = types.Content(role="user", parts=[types.Part.from_text(text="Solve 100 - 20 + 10")])
        events = []
        async for ev in runner.run_async(user_id=user_id, session_id=session_id, new_message=msg):
            events.append(ev)

        assert len(events) > 0
        final_text = "".join(
            p.text for ev in events if ev.content for p in ev.content.parts if p.text
        )
        assert "Problem Decomposition & Premises" in final_text
        assert "Step-by-Step Chain of Thought" in final_text
        assert "90 items remain" in final_text

    asyncio.run(_run())
