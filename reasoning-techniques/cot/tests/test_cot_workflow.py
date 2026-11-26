"""Unit tests for the two-stage Chain-of-Thought (Reasoner -> Verifier) workflow."""

import asyncio
from pathlib import Path
import sys
from typing import AsyncGenerator
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.adk.agents import BaseAgent, InvocationContext, LlmAgent
from google.adk.events import Event
from google.adk.runners import InMemoryRunner
from google.adk.workflow import Workflow, START
from google.genai import types

from cot_agent import create_cot_workflow


class MockReasonerAgent(BaseAgent):
    name: str = "CoTReasoner"
    output_key: str = "reasoning_chain"

    async def _run_async_impl(
        self, context: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        from google.adk.events import EventActions

        thought = (
            "1. Problem: 2x = 10.\n"
            "2. Step 1: Divide both sides by 2.\n"
            "3. Step 2: x = 5.\n"
            "Proposed Answer: x = 5."
        )
        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=thought)],
            ),
            actions=EventActions(state_delta={"reasoning_chain": thought}),
        )


class MockVerifierAgent(BaseAgent):
    name: str = "CoTVerifier"
    output_key: str = "verified_answer"

    async def _run_async_impl(
        self, context: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        from google.adk.events import EventActions

        reasoning = context.session.state.get("reasoning_chain", "")
        verification = (
            f"### Verification Audit\n"
            f"- Step Validity: VALID\n"
            f"- Checked reasoning: {len(reasoning)} chars\n\n"
            f"### Final Verified Answer\nx = 5 is certified correct."
        )
        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=verification)],
            ),
            actions=EventActions(state_delta={"verified_answer": verification}),
        )



def test_workflow_initialization():
    wf = create_cot_workflow(model_name="test-model")
    assert isinstance(wf, Workflow)
    assert wf.name == "cot_workflow_pipeline"
    assert len(wf.edges) == 2


def test_mock_workflow_execution_and_state():
    async def _test():
        reasoner = MockReasonerAgent()
        verifier = MockVerifierAgent()

        wf = Workflow(
            name="test_cot_wf",
            edges=[
                (START, reasoner),
                (reasoner, verifier),
            ],
        )

        runner = InMemoryRunner(wf)
        user_id = "test_user"
        session_id = "test_session_wf"

        await runner.session_service.create_session(
            app_name=runner.app_name, user_id=user_id, session_id=session_id
        )

        msg = types.Content(role="user", parts=[types.Part.from_text(text="Solve 2x = 10")])

        events = []
        async for ev in runner.run_async(user_id=user_id, session_id=session_id, new_message=msg):
            events.append(ev)

        authors = [e.author for e in events]
        assert "CoTReasoner" in authors
        assert "CoTVerifier" in authors

        session = await runner.session_service.get_session(
            app_name=runner.app_name, user_id=user_id, session_id=session_id
        )

        assert "reasoning_chain" in session.state
        assert "verified_answer" in session.state
        assert "x = 5" in session.state["reasoning_chain"]
        assert "VALID" in session.state["verified_answer"]

    asyncio.run(_test())
