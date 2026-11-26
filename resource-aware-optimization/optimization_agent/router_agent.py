"""Resource-Aware Optimization Pattern with Google ADK.

This module implements dynamic query routing between lightweight (Flash)
and high-capacity (Pro) LLM agents based on query complexity analysis.
It minimizes latency and inference costs while ensuring sufficient reasoning
power for complex tasks.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
import os
import re
import sys
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from dotenv import load_dotenv
from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types
from pydantic import Field

# Load environment variables
load_dotenv()

# Model configurations
DEFAULT_FLASH_MODEL = os.getenv("FLASH_MODEL_NAME") or os.getenv("GEMINI_MODEL_NAME") or "gemini-2.5-flash"
DEFAULT_PRO_MODEL = os.getenv("PRO_MODEL_NAME") or "gemini-2.5-pro"


class ResourceTier(str, Enum):
    """Resource allocation tier representing model compute capacity."""
    LIGHTWEIGHT = "lightweight"      # Fast, economical (e.g., Flash)
    HIGH_CAPACITY = "high_capacity"  # Deep reasoning, higher cost (e.g., Pro)


@dataclass
class ComplexityAnalysis:
    """Detailed breakdown of query complexity and resource allocation rationale."""
    score: float
    tier: ResourceTier
    word_count: int
    char_count: int
    detected_factors: List[str] = field(default_factory=list)
    reason: str = ""
    cost_efficiency_estimate: str = ""


# Keywords and markers indicative of high-complexity reasoning tasks
COMPLEX_INDICATORS = [
    "architect", "architecture", "system design", "microservices", "distributed",
    "step-by-step", "trade-off", "tradeoff", "trade-offs", "tradeoffs",
    "optimize", "optimization", "refactor", "algorithm", "time complexity",
    "space complexity", "concurrency", "deadlock", "race condition",
    "security vulnerability", "audit", "critique", "compare and contrast",
    "formal proof", "mathematical proof", "derive", "derivation", "benchmark",
    "root cause", "deep dive", "fault-tolerant", "scalability", "sharding",
    "consensus", "byzantine", "idempotent", "acid transaction"
]

CODE_SYNTAX_MARKERS = [
    "```", "def ", "class ", "select ", "from ", "where ", "import ",
    "async def ", "function", "lambda ", "=>"
]


def analyze_query_complexity(query: str, threshold: float = 0.5) -> ComplexityAnalysis:
    """Evaluates query complexity using multi-dimensional heuristics.

    Args:
        query: User input query text.
        threshold: Score threshold (0.0 - 1.0) above which HIGH_CAPACITY is selected.

    Returns:
        ComplexityAnalysis containing numerical score, tier, detected factors, and reason.
    """
    clean_query = query.strip()
    words = clean_query.split()
    word_count = len(words)
    char_count = len(clean_query)
    q_lower = clean_query.lower()

    score = 0.0
    detected_factors: List[str] = []

    # 1. Length-based heuristics (0.05 to 0.45)
    if word_count < 15:
        score += 0.05
    elif word_count < 30:
        score += 0.15
    elif word_count < 60:
        score += 0.30
        detected_factors.append(f"Moderate query length ({word_count} words)")
    else:
        score += 0.45
        detected_factors.append(f"Extensive query length ({word_count} words)")

    # 2. Domain complexity and reasoning keywords (up to 0.45)
    matched_keywords = [kw for kw in COMPLEX_INDICATORS if kw in q_lower]
    if matched_keywords:
        kw_score = min(0.45, len(matched_keywords) * 0.15)
        score += kw_score
        preview = ", ".join(f"'{k}'" for k in matched_keywords[:3])
        detected_factors.append(f"Complex domain keywords detected ({preview})")

    # 3. Code, syntax, and structured query markers (up to 0.25)
    has_code_syntax = "```" in clean_query or any(marker in q_lower for marker in CODE_SYNTAX_MARKERS)
    if has_code_syntax:
        score += 0.25
        detected_factors.append("Code snippets or programming syntax detected")

    # 4. Multi-step / structured requirement markers (up to 0.20)
    question_count = clean_query.count("?")
    if question_count > 1:
        score += min(0.15, question_count * 0.05)
        detected_factors.append(f"Multiple inquiries detected ({question_count} question marks)")

    if re.search(r"(?m)^(?:\d+\.|\*|-)\s+\w+", clean_query):
        score += 0.10
        detected_factors.append("Structured list or multi-step requirements detected")

    # Bound score within [0.0, 1.0]
    final_score = max(0.0, min(1.0, round(score, 2)))

    if final_score >= threshold:
        tier = ResourceTier.HIGH_CAPACITY
        factors_str = "; ".join(detected_factors) if detected_factors else "High length/density"
        reason = (
            f"Complexity score {final_score:.2f} >= threshold {threshold:.2f}. "
            f"Allocated High-Capacity Pro tier for deep reasoning. Factors: {factors_str}."
        )
        cost_savings = "Resource-intensive tier allocated (~1.0x baseline cost)"
    else:
        tier = ResourceTier.LIGHTWEIGHT
        reason = (
            f"Complexity score {final_score:.2f} < threshold {threshold:.2f}. "
            f"Allocated Lightweight Flash tier for low latency and ~85-90% token cost reduction."
        )
        cost_savings = "Optimized with Flash (~0.1x baseline cost, ~85-90% savings)"

    return ComplexityAnalysis(
        score=final_score,
        tier=tier,
        word_count=word_count,
        char_count=char_count,
        detected_factors=detected_factors,
        reason=reason,
        cost_efficiency_estimate=cost_savings,
    )

def create_flash_agent(model_name: Optional[str] = None) -> LlmAgent:
    """Builds the lightweight, high-speed Flash agent."""
    model = model_name or DEFAULT_FLASH_MODEL
    return LlmAgent(
        name="GeminiFlashAgent",
        model=model,
        description="A fast and economical agent for simple to moderate queries.",
        instruction=(
            "You are a fast, concise, and helpful assistant. "
            "Provide accurate and direct responses without unnecessary fluff."
        ),
        generate_content_config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=500,
        ),
    )


def create_pro_agent(model_name: Optional[str] = None) -> LlmAgent:
    """Builds the high-capacity, deep-reasoning Pro agent."""
    model = model_name or DEFAULT_PRO_MODEL
    return LlmAgent(
        name="GeminiProAgent",
        model=model,
        description="A highly capable agent for complex problem-solving, analysis, and architecture.",
        instruction=(
            "You are an expert AI assistant specialized in complex problem-solving, "
            "architectural design, comprehensive analysis, and meticulous explanations. "
            "Provide thorough, high-quality, and well-structured responses."
        ),
        generate_content_config=types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=1200,
            thinking_config=types.ThinkingConfig(thinking_budget=512),
        ),
    )


# Default agent instances
gemini_flash_agent = create_flash_agent()
gemini_pro_agent = create_pro_agent()


class QueryRouterAgent(BaseAgent):
    """Resource-aware routing agent that dynamically dispatches queries based on complexity."""

    name: str = "QueryRouter"
    description: str = "Routes user queries to the appropriate LLM agent based on complexity and resource awareness."
    complexity_threshold: float = 0.5
    flash_agent: BaseAgent = Field(default_factory=create_flash_agent)
    pro_agent: BaseAgent = Field(default_factory=create_pro_agent)
    sub_agents: List[BaseAgent] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        """Ensure sub-agents are properly registered with the ADK hierarchy."""
        super().model_post_init(__context)
        if not self.sub_agents:
            self.sub_agents = [self.flash_agent, self.pro_agent]

    @staticmethod
    def extract_query_text(context: InvocationContext) -> str:
        """Extracts text content from the invocation context or session events."""
        if context.user_content and context.user_content.parts:
            parts_text = [
                part.text for part in context.user_content.parts if getattr(part, "text", None)
            ]
            if parts_text:
                return " ".join(parts_text).strip()

        if context.session and context.session.events:
            for event in reversed(context.session.events):
                if event.author == "user" and event.content and event.content.parts:
                    parts_text = [
                        p.text for p in event.content.parts if getattr(p, "text", None)
                    ]
                    if parts_text:
                        return " ".join(parts_text).strip()

        return ""

    async def _run_async_impl(
        self, context: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Analyzes incoming query, routes to optimal agent, and logs telemetry."""
        user_query = self.extract_query_text(context)
        analysis = analyze_query_complexity(user_query, self.complexity_threshold)

        if analysis.tier == ResourceTier.LIGHTWEIGHT:
            target_agent = self.flash_agent
            chosen_model = getattr(target_agent, "canonical_model", DEFAULT_FLASH_MODEL)
        else:
            target_agent = self.pro_agent
            chosen_model = getattr(target_agent, "canonical_model", DEFAULT_PRO_MODEL)

        # Notify routing decision and persist routing telemetry in session state
        routing_telemetry = {
            "query": user_query[:120],
            "complexity_score": analysis.score,
            "threshold": self.complexity_threshold,
            "tier": analysis.tier.value,
            "target_agent": target_agent.name,
            "model": str(chosen_model),
            "reason": analysis.reason,
            "cost_efficiency": analysis.cost_efficiency_estimate,
        }

        yield Event(
            author=self.name,
            actions=EventActions(
                state_delta={
                    "last_routing": routing_telemetry,
                    "resource_tier": analysis.tier.value,
                    "target_agent": target_agent.name,
                }
            ),
            content=types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text=(
                            f"[Resource-Aware Optimizer] Routed to {target_agent.name} "
                            f"(Tier: {analysis.tier.value.upper()}, Score: {analysis.score:.2f}). "
                            f"{analysis.reason}"
                        )
                    )
                ],
            ),
        )

        start_time = time.perf_counter()

        # Delegate execution to the selected specialized agent
        async for event in target_agent.run_async(context):
            yield event

        elapsed = time.perf_counter() - start_time

        # Update session state with completed performance metrics
        yield Event(
            author=self.name,
            actions=EventActions(
                state_delta={
                    "last_execution_latency_seconds": round(elapsed, 3),
                    "routing_completed": True,
                }
            ),
        )

__all__ = [
    "ResourceTier",
    "ComplexityAnalysis",
    "COMPLEX_INDICATORS",
    "CODE_SYNTAX_MARKERS",
    "analyze_query_complexity",
    "create_flash_agent",
    "create_pro_agent",
    "gemini_flash_agent",
    "gemini_pro_agent",
    "QueryRouterAgent",
]





    
