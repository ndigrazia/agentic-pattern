"""Unit tests for the ReAct Agent configuration, prompts, and execution cycle."""

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

from react_agent import (
    DIRECT_SYSTEM_INSTRUCTION,
    FEW_SHOT_REACT_EXEMPLARS,
    REACT_SYSTEM_INSTRUCTION,
    build_react_instruction,
    create_direct_agent,
    create_react_agent,
    get_default_model,
)


class MockReActAgent(BaseAgent):
    """Deterministic mock agent simulating a full ReAct Thought-Action-Observation loop."""
    name: str = "react_agent"

    async def _run_async_impl(
        self, context: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # 1. Thought 1
        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(
                    text="Thought: I need to check memory usage for auth-service first."
                )],
            ),
        )

        # 2. Action (Tool Call)
        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part.from_function_call(
                    name="system_metrics_query",
                    args={"service_name": "auth-service", "metric": "memory_usage_pct"},
                )],
            ),
        )

        # 3. Observation (Tool Result)
        yield Event(
            author="system_metrics_query",
            content=types.Content(
                role="user",
                parts=[types.Part.from_function_response(
                    name="system_metrics_query",
                    response={"result": "auth-service memory_usage_pct: 86.2"},
                )],
            ),
        )

        # 4. Final Thought & Answer
        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(
                    text=(
                        "Thought: The memory is 86.2%, which exceeds the 80% threshold.\n"
                        "Final Answer: auth-service memory utilization is 86.2%."
                    )
                )],
            ),
        )


def test_react_agent_initialization_defaults():
    agent = create_react_agent()
    assert isinstance(agent, LlmAgent)
    assert agent.name == "react_agent"
    assert "ReAct" in agent.description
    assert len(agent.tools) == 4
    tool_names = {t.name for t in agent.tools}
    assert tool_names == {
        "search_knowledge_base",
        "calculator",
        "system_metrics_query",
        "database_lookup",
    }
    assert "Thought:" in agent.instruction
    assert "Action:" in agent.instruction
    assert "Observation:" in agent.instruction
    assert "Final Answer:" in agent.instruction


def test_react_agent_few_shot_mode():
    agent = create_react_agent(mode="few-shot")
    assert "ReAct Few-Shot Exemplars" in agent.instruction
    assert "Incident Triage" in agent.instruction
    assert "Financial Growth Rate" in agent.instruction


def test_react_agent_zero_shot_mode():
    agent = create_react_agent(mode="zero-shot")
    assert "ReAct Few-Shot Exemplars" not in agent.instruction
    assert "Core ReAct Loop" in agent.instruction


def test_react_agent_custom_model_and_tools_toggle():
    agent = create_react_agent(model_name="custom-test-model", enable_tools=False)
    assert agent.model == "custom-test-model"
    assert len(agent.tools) == 0


def test_direct_agent_baseline():
    direct = create_direct_agent(model_name="direct-test-model")
    assert direct.model == "direct-test-model"
    assert direct.name == "direct_agent"
    assert "without showing intermediate thinking steps" in direct.instruction
    assert len(direct.tools) == 0


def test_mock_runner_execution_react_loop():
    async def _run():
        agent = MockReActAgent()
        runner = InMemoryRunner(agent)
        user_id = "test_user"
        session_id = "test_session_react"

        await runner.session_service.create_session(
            app_name=runner.app_name, user_id=user_id, session_id=session_id
        )

        msg = types.Content(
            role="user",
            parts=[types.Part.from_text(text="Check auth-service memory status")],
        )

        events = []
        async for ev in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=msg
        ):
            events.append(ev)

        assert len(events) >= 3

        # Check for Thought
        texts = [
            p.text
            for ev in events
            if ev.content
            for p in ev.content.parts
            if getattr(p, "text", None)
        ]
        assert any("Thought: I need to check" in t for t in texts)
        assert any("Final Answer:" in t for t in texts)

        # Check for Action
        actions = [
            p.function_call
            for ev in events
            if ev.content
            for p in ev.content.parts
            if getattr(p, "function_call", None)
        ]
        assert len(actions) == 1
        assert actions[0].name == "system_metrics_query"

        # Check for Observation
        observations = [
            p.function_response
            for ev in events
            if ev.content
            for p in ev.content.parts
            if getattr(p, "function_response", None)
        ]
        assert len(observations) == 1
        assert "86.2" in str(observations[0].response)

    asyncio.run(_run())
