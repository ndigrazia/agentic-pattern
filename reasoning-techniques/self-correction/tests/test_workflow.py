"""Unit tests for the two-stage Self-Correction workflow."""

import asyncio
from pathlib import Path
import sys
from typing import AsyncGenerator
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.adk.agents import BaseAgent, InvocationContext
from google.adk.events import Event, EventActions
from google.adk.runners import InMemoryRunner
from google.adk.workflow import Workflow, START
from google.genai import types

from self_correction_agent import create_self_correction_workflow


class MockDraftWriter(BaseAgent):
    name: str = "DraftWriter"
    output_key: str = "draft_content"

    async def _run_async_impl(
        self, context: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        draft = "We have new products. They are green and techy. Buy GreenTech Gadgets now!"
        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=draft)],
            ),
            actions=EventActions(state_delta={"draft_content": draft}),
        )


class MockCritic(BaseAgent):
    name: str = "SelfCorrectionCritic"
    output_key: str = "corrected_content"

    async def _run_async_impl(
        self, context: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        draft = context.session.state.get("draft_content", "")
        corrected = (
            f"Critiqued draft: '{draft}'.\n"
            "Revised: 🌱 Discover GreenTech Gadgets! Our new eco-friendly line blends "
            "innovation with sustainability. Go green, go smart! Shop now! #EcoFriendly #GreenTech"
        )
        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=corrected)],
            ),
            actions=EventActions(state_delta={"corrected_content": corrected}),
        )


def test_workflow_initialization():
    wf = create_self_correction_workflow(model_name="test-model")
    assert isinstance(wf, Workflow)
    assert wf.name == "self_correction_pipeline"
    assert len(wf.edges) == 2


def test_mock_workflow_execution():
    async def _test():
        draft_agent = MockDraftWriter()
        critic_agent = MockCritic()

        wf = Workflow(
            name="test_self_correction_wf",
            edges=[
                (START, draft_agent),
                (draft_agent, critic_agent),
            ],
        )

        runner = InMemoryRunner(wf)
        user_id = "test_user"
        session_id = "test_wf_session"

        await runner.session_service.create_session(
            app_name=runner.app_name, user_id=user_id, session_id=session_id
        )

        msg = types.Content(
            role="user",
            parts=[types.Part.from_text(text="Launch GreenTech Gadgets line")],
        )

        events = []
        async for ev in runner.run_async(user_id=user_id, session_id=session_id, new_message=msg):
            events.append(ev)

        authors = [e.author for e in events]
        assert "DraftWriter" in authors
        assert "SelfCorrectionCritic" in authors

        session = await runner.session_service.get_session(
            app_name=runner.app_name, user_id=user_id, session_id=session_id
        )

        assert "draft_content" in session.state
        assert "corrected_content" in session.state
        assert "GreenTech Gadgets" in session.state["corrected_content"]

    asyncio.run(_test())
