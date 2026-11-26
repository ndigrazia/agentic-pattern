"""CLI entrypoint and runner helpers for the Resource-Aware Optimization Pattern.

This module orchestrates agent execution using Google ADK's InMemoryRunner,
tracks execution metrics (latency, token consumption, cost savings),
and provides CLI modes including single-prompt, multi-query demo, and interactive REPL.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
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

load_dotenv()


async def run_query(
    prompt: str,
    threshold: float = 0.5,
    verbose: bool = True,
    flash_model: Optional[str] = None,
    pro_model: Optional[str] = None,
) -> Dict[str, Any]:
    """Runs a query through the resource-aware optimization router.

    Args:
        prompt: User input prompt string.
        threshold: Complexity score cutoff for routing to Pro.
        verbose: Whether to print streaming events and routing info.
        flash_model: Custom model for flash agent.
        pro_model: Custom model for pro agent.

    Returns:
        Structured dictionary containing routing decision, response text, and telemetry.
    """
    f_agent = create_flash_agent(flash_model)
    p_agent = create_pro_agent(pro_model)
    router = QueryRouterAgent(
        complexity_threshold=threshold,
        flash_agent=f_agent,
        pro_agent=p_agent,
        sub_agents=[f_agent, p_agent],
    )

    runner = InMemoryRunner(router)
    user_id = "user_default"
    session_id = f"session_{int(time.time() * 1000)}"

    await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )

    message = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])

    if verbose:
        print("\n" + "=" * 70)
        print(f"📥 Query: {prompt}")
        print("=" * 70)

    analysis = analyze_query_complexity(prompt, threshold)
    if verbose:
        tier_symbol = "⚡" if analysis.tier == ResourceTier.LIGHTWEIGHT else "🧠"
        print(f"{tier_symbol} Resource Analysis: Score={analysis.score:.2f} | Tier={analysis.tier.value.upper()}")
        print(f"   Reason: {analysis.reason}")
        print(f"   Cost:   {analysis.cost_efficiency_estimate}\n")

    response_text_parts: List[str] = []
    agent_author: Optional[str] = None
    token_usage: Dict[str, Any] = {}
    start_time = time.perf_counter()

    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=message
    ):
        if event.usage_metadata:
            token_usage = {
                "prompt_tokens": event.usage_metadata.prompt_token_count,
                "candidate_tokens": event.usage_metadata.candidates_token_count,
                "total_tokens": event.usage_metadata.total_token_count,
            }

        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    if event.author == router.name:
                        if verbose:
                            print(f"[{event.author}]: {part.text}")
                    else:
                        agent_author = event.author
                        response_text_parts.append(part.text)
                        if verbose:
                            print(f"[{event.author}]: {part.text}")

    elapsed_time = time.perf_counter() - start_time
    final_response = "".join(response_text_parts).strip()

    # Retrieve updated session state
    updated_session = await runner.session_service.get_session(
        app_name=runner.app_name, user_id=user_id, session_id=session_id
    )
    final_state = updated_session.state if updated_session else {}

    result = {
        "prompt": prompt,
        "response": final_response,
        "executing_agent": agent_author,
        "complexity_analysis": analysis,
        "token_usage": token_usage,
        "elapsed_seconds": round(elapsed_time, 3),
        "session_state": final_state,
    }

    if verbose:
        print("-" * 70)
        print(f"⏱️  Duration: {result['elapsed_seconds']}s")
        if token_usage:
            print(f"📊 Tokens: {token_usage}")
        print("=" * 70 + "\n")

    return result

async def run_demo() -> None:
    """Executes a demonstration of Resource-Aware Optimization with distinct complexity queries."""
    print("\n" + "#" * 70)
    print("#  Resource-Aware Optimization Pattern Demo")
    print("#" * 70)

    demo_queries = [
        # 1. Simple factual query -> Should route to Flash
        "What is the boiling point of water in Celsius?",
        # 2. Straightforward programming explanation -> Should route to Flash
        "Briefly explain what a Python dictionary is in two sentences.",
        # 3. High-complexity architectural & algorithm design -> Should route to Pro
        (
            "Design a fault-tolerant, high-throughput distributed event streaming architecture "
            "using Kafka, sharding, and consensus protocols. Analyze the trade-offs between "
            "strict consistency and availability under network partitions, and optimize for sub-10ms latency."
        ),
    ]

    results = []
    for query in demo_queries:
        res = await run_query(query, threshold=0.5, verbose=True)
        results.append(res)

    print("\n" + "=" * 70)
    print("📈 DEMO SUMMARY: Resource-Aware Allocation Results")
    print("=" * 70)
    print(f"{'#':<3} | {'Tier':<14} | {'Agent':<18} | {'Score':<6} | {'Time (s)':<8} | Query Preview")
    print("-" * 70)
    for i, res in enumerate(results, 1):
        ca: ComplexityAnalysis = res["complexity_analysis"]
        preview = res["prompt"][:35] + ("..." if len(res["prompt"]) > 35 else "")
        agent = res["executing_agent"] or "N/A"
        print(
            f"{i:<3} | {ca.tier.value:<14} | {agent:<18} | {ca.score:<6.2f} | "
            f"{res['elapsed_seconds']:<8.2f} | {preview}"
        )
    print("=" * 70 + "\n")


async def interactive_mode(threshold: float = 0.5) -> None:
    """Runs an interactive REPL allowing user to test various queries."""
    print("\n" + "=" * 70)
    print("🤖 Resource-Aware Optimization Interactive REPL")
    print("Type your query to see real-time complexity analysis and model routing.")
    print("Type 'exit' or 'quit' to terminate.")
    print("=" * 70 + "\n")

    while True:
        try:
            query = input("Enter query > ").strip()
            if not query:
                continue
            if query.lower() in ("exit", "quit", "q"):
                print("Exiting interactive session.")
                break
            await run_query(query, threshold=threshold, verbose=True)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting interactive session.")
            break


def main() -> None:
    """CLI entry point for running the pattern."""
    parser = argparse.ArgumentParser(
        description="Resource-Aware Optimization Pattern with Google ADK"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="A single prompt to run through the resource-aware router.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Complexity score threshold for routing to High-Capacity Pro tier (default: 0.5).",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run the multi-query demonstration suite.",
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run an interactive command-line session.",
    )

    args = parser.parse_args()

    if args.interactive:
        asyncio.run(interactive_mode(threshold=args.threshold))
    elif args.prompt:
        asyncio.run(run_query(args.prompt, threshold=args.threshold, verbose=True))
    else:
        # Default behavior: run demonstration
        asyncio.run(run_demo())


if __name__ == "__main__":
    main()

