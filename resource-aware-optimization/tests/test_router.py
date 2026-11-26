"""Unit tests for the Resource-Aware Optimization pattern."""

import asyncio
import os
from pathlib import Path
import sys
from typing import AsyncGenerator
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.adk.agents import BaseAgent, InvocationContext

from google.adk.events import Event, EventActions
from google.adk.runners import InMemoryRunner
from google.genai import types

from optimization_agent import (
    ComplexityAnalysis,
    QueryRouterAgent,
    ResourceTier,
    analyze_query_complexity,
    create_flash_agent,
    create_pro_agent,
)


class MockSubAgent(BaseAgent):
    """Deterministic mock agent for unit testing router delegation."""
    name: str = "MockAgent"
    response_text: str = "Mock response content"

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


def test_analyze_query_complexity_simple():
    """Simple, short queries should be classified as LIGHTWEIGHT."""
    queries = [
        "What is 2 + 2?",
        "What is the capital of France?",
        "Hi, how are you?",
        "Define gravity in one sentence.",
    ]
    for q in queries:
        analysis = analyze_query_complexity(q, threshold=0.5)
        assert analysis.tier == ResourceTier.LIGHTWEIGHT
        assert analysis.score < 0.5
        assert "Flash" in analysis.cost_efficiency_estimate


def test_analyze_query_complexity_complex():
    """Queries involving distributed architecture, concurrency, or algorithms should be HIGH_CAPACITY."""
    complex_q = (
        "Design a fault-tolerant distributed system architecture with microservices, "
        "consensus protocols, and database sharding. Analyze latency vs consistency trade-offs."
    )
    analysis = analyze_query_complexity(complex_q, threshold=0.5)
    assert analysis.tier == ResourceTier.HIGH_CAPACITY
    assert analysis.score >= 0.5
    assert len(analysis.detected_factors) > 0
    assert "Pro" in analysis.reason


def test_analyze_query_complexity_code_snippet():
    """Code snippets and programming markers increase complexity."""
    code_q = "```python\ndef fib(n):\n    return n if n <= 1 else fib(n-1) + fib(n-2)\n``` optimize this."
    analysis = analyze_query_complexity(code_q, threshold=0.3)
    assert any("Code snippets" in factor for factor in analysis.detected_factors)
    assert analysis.tier == ResourceTier.HIGH_CAPACITY


def test_custom_threshold():
    """Custom thresholds should alter the routing decision."""
    query = "Provide a step-by-step optimization for binary search trees."
    analysis_high = analyze_query_complexity(query, threshold=0.5)
    assert analysis_high.tier == ResourceTier.LIGHTWEIGHT

    analysis_low = analyze_query_complexity(query, threshold=0.2)
    assert analysis_low.tier == ResourceTier.HIGH_CAPACITY

def test_router_agent_initialization():
    """QueryRouterAgent initializes correctly with sub-agents registered."""
    flash = MockSubAgent(name="FlashMock")
    pro = MockSubAgent(name="ProMock")
    router = QueryRouterAgent(
        complexity_threshold=0.6,
        flash_agent=flash,
        pro_agent=pro,
    )
    assert router.complexity_threshold == 0.6
    assert len(router.sub_agents) == 2
    assert router.sub_agents[0].name == "FlashMock"
    assert router.sub_agents[1].name == "ProMock"


def test_extract_query_text_from_context():
    """Extracts text correctly from user_content in InvocationContext."""
    class DummyContext:
        user_content = types.Content(
            role="user", parts=[types.Part.from_text(text="Test query text")]
        )
        session = None

    extracted = QueryRouterAgent.extract_query_text(DummyContext())
    assert extracted == "Test query text"


def test_router_delegates_to_flash():
    """Router correctly delegates simple queries to the Flash agent."""
    async def _async_test():
        flash_mock = MockSubAgent(name="GeminiFlashAgent", response_text="Answer from Flash")
        pro_mock = MockSubAgent(name="GeminiProAgent", response_text="Answer from Pro")

        router = QueryRouterAgent(
            complexity_threshold=0.5,
            flash_agent=flash_mock,
            pro_agent=pro_mock,
            sub_agents=[flash_mock, pro_mock],
        )

        runner = InMemoryRunner(router)
        user_id = "test_user"
        session_id = "test_session_flash"

        await runner.session_service.create_session(
            app_name=runner.app_name, user_id=user_id, session_id=session_id
        )

        message = types.Content(
            role="user", parts=[types.Part.from_text(text="What is 1 + 1?")]
        )

        events = []
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=message
        ):
            events.append(event)

        authors = [e.author for e in events]
        assert "QueryRouter" in authors
        assert "GeminiFlashAgent" in authors
        assert "GeminiProAgent" not in authors

        session = await runner.session_service.get_session(
            app_name=runner.app_name, user_id=user_id, session_id=session_id
        )
        assert session.state["resource_tier"] == "lightweight"
        assert session.state["target_agent"] == "GeminiFlashAgent"
        assert "last_routing" in session.state
        assert session.state["routing_completed"] is True

    asyncio.run(_async_test())


def test_router_delegates_to_pro():
    """Router correctly delegates complex queries to the Pro agent."""
    async def _async_test():
        flash_mock = MockSubAgent(name="GeminiFlashAgent", response_text="Answer from Flash")
        pro_mock = MockSubAgent(name="GeminiProAgent", response_text="Answer from Pro")

        router = QueryRouterAgent(
            complexity_threshold=0.5,
            flash_agent=flash_mock,
            pro_agent=pro_mock,
            sub_agents=[flash_mock, pro_mock],
        )

        runner = InMemoryRunner(router)
        user_id = "test_user"
        session_id = "test_session_pro"

        await runner.session_service.create_session(
            app_name=runner.app_name, user_id=user_id, session_id=session_id
        )

        complex_prompt = (
            "Design a distributed system architecture with microservices, consensus, "
            "and sharding. Analyze trade-offs."
        )
        message = types.Content(
            role="user", parts=[types.Part.from_text(text=complex_prompt)]
        )

        events = []
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=message
        ):
            events.append(event)

        authors = [e.author for e in events]
        assert "QueryRouter" in authors
        assert "GeminiProAgent" in authors
        assert "GeminiFlashAgent" not in authors

        session = await runner.session_service.get_session(
            app_name=runner.app_name, user_id=user_id, session_id=session_id
        )
        assert session.state["resource_tier"] == "high_capacity"
        assert session.state["target_agent"] == "GeminiProAgent"
        assert session.state["routing_completed"] is True

    asyncio.run(_async_test())


