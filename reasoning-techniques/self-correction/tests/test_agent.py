"""Unit tests for the Self-Correction Agent and prompt configurations."""

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

from self_correction_agent import (
    SELF_CORRECTION_SYSTEM_INSTRUCTION,
    build_self_correction_instruction,
    create_draft_agent,
    create_self_correction_agent,
    get_default_model,
)


class MockSelfCorrectionAgent(BaseAgent):
    """Deterministic mock agent simulating the 5-step self-correction process."""
    name: str = "self_correction_agent"
    response_text: str = (
        "### Self-Correction Agent's Thought Process (Internal CoT Output):\n"
        "**Thought 1 (Understand Original Requirements):**\n"
        "- Social post, max 150 chars, announce GreenTech Gadgets eco-friendly line.\n\n"
        "**Thought 2 (Analyze Current Content):**\n"
        "\"We have new products. They are green and techy. Buy GreenTech Gadgets now!\" (74 chars)\n\n"
        "**Thought 3 (Identify Discrepancies/Weaknesses):**\n"
        "- Not engaging, doesn't emphasize sustainability benefits.\n\n"
        "**Thought 4 (Propose Specific Improvements):**\n"
        "- Add emojis, stronger call to action, keep under 150 chars.\n\n"
        "**Thought 5 (Generate Revised Content):**\n"
        "- Revised: \"🌱 Discover GreenTech Gadgets! Our new eco-friendly line blends innovation with sustainability. Go green, go smart! Shop now! #EcoFriendly #GreenTech\" (148 chars)\n\n"
        "### Self-Correction Agent's Final Revised Content (Output to User):\n"
        "🌱 Discover GreenTech Gadgets! Our new eco-friendly line blends innovation with sustainability. Go green, go smart! Shop now! #EcoFriendly #GreenTech"
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


def test_self_correction_agent_initialization():
    agent = create_self_correction_agent()
    assert isinstance(agent, LlmAgent)
    assert agent.name == "self_correction_agent"
    assert "Self-Correction Agent" in agent.description
    assert len(agent.tools) == 2
    tool_names = [t.name for t in agent.tools]
    assert "analyze_text_metrics" in tool_names
    assert "verify_constraint_checklist" in tool_names

    # Check key 5-step phrases in instruction
    assert "Understand Original Requirements" in agent.instruction
    assert "Analyze Current Content" in agent.instruction
    assert "Identify Discrepancies/Weaknesses" in agent.instruction
    assert "Propose Specific Improvements" in agent.instruction
    assert "Generate Revised Content" in agent.instruction
    assert "GreenTech Gadgets" in agent.instruction


def test_self_correction_agent_custom_options():
    agent = create_self_correction_agent(
        model_name="gemini-test-model",
        mode="zero-shot",
        enable_tools=False,
    )
    assert agent.model == "gemini-test-model"
    assert len(agent.tools) == 0
    assert "Exemplar Demonstrations" not in agent.instruction


def test_draft_agent_initialization():
    draft_agent = create_draft_agent(model_name="custom-model")
    assert isinstance(draft_agent, LlmAgent)
    assert draft_agent.name == "draft_writer"
    assert draft_agent.model == "custom-model"


def test_mock_self_correction_runner():
    async def _run():
        agent = MockSelfCorrectionAgent()
        runner = InMemoryRunner(agent)
        user_id = "test_user"
        session_id = "test_sess"

        await runner.session_service.create_session(
            app_name=runner.app_name, user_id=user_id, session_id=session_id
        )

        msg = types.Content(role="user", parts=[types.Part.from_text(text="Review draft")])
        events = []
        async for ev in runner.run_async(user_id=user_id, session_id=session_id, new_message=msg):
            events.append(ev)

        assert len(events) > 0
        final_text = "".join(
            p.text for ev in events if ev.content for p in ev.content.parts if p.text
        )
        assert "Thought 1 (Understand Original Requirements)" in final_text
        assert "Thought 5 (Generate Revised Content)" in final_text
        assert "🌱 Discover GreenTech Gadgets!" in final_text

    asyncio.run(_run())


def test_compare_import_and_helpers():
    from compare import compare_alternatives
    from main import format_user_query, DEFAULT_PROMPT_CASE

    query = format_user_query("req", "draft")
    assert "Original Prompt/Requirements" in query
    assert "Initial Draft" in query
    assert callable(compare_alternatives)

