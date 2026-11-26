"""CLI entrypoint and demonstration runner for the Chain-of-Thought (CoT) Pattern.

Supports:
- Zero-Shot CoT execution.
- Few-Shot CoT execution with exemplar demonstrations.
- Two-Stage Multi-Agent Workflow (Reasoner -> Verifier).
- Side-by-side comparison between Direct (No CoT) and CoT reasoning.
- Benchmark suite execution across mathematical, logical, and algorithmic problems.
- Interactive REPL.
"""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

# Ensure package directory is in sys.path
base_dir = Path(__file__).resolve().parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from google.genai import types

from cot_agent import (
    create_cot_agent,
    create_cot_workflow,
    create_direct_agent,
    get_default_model,
)

load_dotenv()

BENCHMARK_PROMPTS = [
    {
        "category": "Multi-Step Arithmetic & Inventory",
        "question": (
            "A bookstore has 240 novels. On Monday, it sells 25% of them. "
            "On Tuesday, it receives a new shipment of 60 novels and then sells 1/3 of its total stock. "
            "On Wednesday, 15 novels are set aside for a reading club. "
            "How many novels remain available for sale?"
        ),
    },
    {
        "category": "Deductive Logic & Seating Constraints",
        "question": (
            "Four colleagues—Dana, Evan, Fiona, and George—are seated in a row of four chairs (1 to 4, left to right). "
            "1. Dana is not sitting in chair 1 or chair 4. "
            "2. Evan sits immediately to the left of Fiona. "
            "3. George is sitting in chair 4. "
            "Determine the exact chair number (1 to 4) for each person."
        ),
    },
    {
        "category": "Algorithmic Recurrence & State Trace",
        "question": (
            "A robot starts at coordinate (0, 0) facing North. It executes the following sequence: "
            "Step 1: Move forward 3 units. "
            "Step 2: Turn 90 degrees clockwise and move forward 4 units. "
            "Step 3: Turn 90 degrees clockwise and move forward 1 unit. "
            "Step 4: Turn 90 degrees clockwise and move forward 2 units. "
            "What is the robot's final coordinate (X, Y) and its straight-line Euclidean distance from the origin?"
        ),
    },
]


async def run_agent_query(
    agent_or_workflow: Any,
    prompt: str,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Runs a prompt through an ADK agent or workflow using InMemoryRunner."""
    runner = InMemoryRunner(agent_or_workflow)
    user_id = "user_default"
    session_id = f"session_{uuid.uuid4().hex[:8]}"

    await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )

    message = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])

    response_text = ""
    event_logs: List[Dict[str, str]] = []
    start_time = time.perf_counter()

    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=message
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "function_call", None):
                    call = part.function_call
                    if verbose:
                        print(f"\n[{event.author} ⚙️ Tool Call]: {call.name}({call.args})")
                elif getattr(part, "function_response", None):
                    resp = part.function_response
                    if verbose:
                        print(f"[{event.author} ⚙️ Tool Result]: {resp.response}")
                elif getattr(part, "text", None):
                    event_logs.append({"author": event.author, "text": part.text})
                    if verbose:
                        print(f"\n[{event.author}]:\n{part.text}")
        if event.is_final_response() and event.content:
            if hasattr(event.content, "text") and event.content.text:
                response_text = event.content.text
            elif event.content.parts:
                response_text = "".join(p.text for p in event.content.parts if p.text)

    elapsed_time = time.perf_counter() - start_time

    session = await runner.session_service.get_session(
        app_name=runner.app_name, user_id=user_id, session_id=session_id
    )

    return {
        "response": response_text or "".join(l["text"] for l in event_logs),
        "events": event_logs,
        "elapsed_seconds": round(elapsed_time, 2),
        "session_state": dict(session.state) if session else {},
    }

async def run_comparison(prompt: str, model_name: Optional[str] = None) -> None:
    """Executes side-by-side comparison between Direct Answering vs CoT Reasoning."""
    print("\n" + "=" * 78)
    print("🔬 COMPARISON: Direct Answering (No CoT) vs Chain-of-Thought (CoT)")
    print("=" * 78)
    print(f"Query: {prompt}\n")

    direct_agent = create_direct_agent(model_name)
    cot_agent = create_cot_agent(model_name=model_name, mode="zero-shot")

    print("--- 1. Direct Answering (Standard LLM Prompt) ---")
    direct_res = await run_agent_query(direct_agent, prompt, verbose=True)
    print(f"\n⏱️ Elapsed Time: {direct_res['elapsed_seconds']}s")

    print("\n" + "-" * 78)
    print("--- 2. Chain-of-Thought Reasoning Agent ---")
    cot_res = await run_agent_query(cot_agent, prompt, verbose=True)
    print(f"\n⏱️ Elapsed Time: {cot_res['elapsed_seconds']}s")

    print("\n" + "=" * 78)
    print("📊 Summary Comparison")
    print(f"Direct Response Latency: {direct_res['elapsed_seconds']}s")
    print(f"CoT Response Latency:    {cot_res['elapsed_seconds']}s")
    print("Note: CoT produces explicit deduction steps and verification before conclusions.")
    print("=" * 78)


async def run_benchmark(model_name: Optional[str] = None) -> None:
    """Runs a multi-domain reasoning benchmark suite."""
    print("\n" + "=" * 78)
    print("🚀 RUNNING CHAIN-OF-THOUGHT BENCHMARK SUITE")
    print("=" * 78)

    cot_agent = create_cot_agent(model_name=model_name, mode="zero-shot")

    for idx, item in enumerate(BENCHMARK_PROMPTS, 1):
        print(f"\n[Problem {idx}/{len(BENCHMARK_PROMPTS)}] Category: {item['category']}")
        print(f"Question: {item['question']}")
        print("-" * 60)
        res = await run_agent_query(cot_agent, item["question"], verbose=True)
        print(f"⏱️ Solved in {res['elapsed_seconds']}s\n")
        print("=" * 78)


async def run_interactive(model_name: Optional[str] = None, mode: str = "zero-shot") -> None:
    """Interactive REPL for Chain-of-Thought reasoning."""
    print("\n" + "=" * 78)
    print(f"💬 Interactive CoT Agent (Mode: {mode}, Model: {model_name or get_default_model()})")
    print("Type your reasoning problem or question. Type 'exit' or 'quit' to end.")
    print("=" * 78 + "\n")

    agent = create_cot_agent(model_name=model_name, mode=mode)

    while True:
        try:
            user_input = input("\n🤔 Enter Question > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                print("Exiting interactive session.")
                break
            await run_agent_query(agent, user_input, verbose=True)
        except (KeyboardInterrupt, EOFError):
            print("\nSession terminated.")
            break


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chain-of-Thought (CoT) Reasoning Agent with Google ADK"
    )
    parser.add_argument(
        "-p", "--prompt",
        type=str,
        help="Input query or reasoning problem to solve",
    )
    parser.add_argument(
        "-m", "--mode",
        type=str,
        choices=["zero-shot", "few-shot", "workflow"],
        default="zero-shot",
        help="CoT technique: zero-shot, few-shot, or two-stage workflow (default: zero-shot)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Gemini model override (e.g. gemini-2.5-flash)",
    )
    parser.add_argument(
        "-c", "--compare",
        action="store_true",
        help="Compare Direct Answering vs CoT Reasoning side-by-side",
    )
    parser.add_argument(
        "-b", "--benchmark",
        action="store_true",
        help="Run multi-domain reasoning benchmark suite",
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Start an interactive REPL session",
    )

    args = parser.parse_args()

    if args.compare:
        prompt = args.prompt or BENCHMARK_PROMPTS[0]["question"]
        asyncio.run(run_comparison(prompt, model_name=args.model))
    elif args.benchmark:
        asyncio.run(run_benchmark(model_name=args.model))
    elif args.interactive:
        asyncio.run(run_interactive(model_name=args.model, mode=args.mode))
    else:
        prompt = args.prompt or BENCHMARK_PROMPTS[0]["question"]
        print(f"\n💡 Running Chain-of-Thought Agent [Mode: {args.mode}]")
        print(f"❓ Prompt: {prompt}\n")

        if args.mode == "workflow":
            workflow = create_cot_workflow(model_name=args.model)
            asyncio.run(run_agent_query(workflow, prompt, verbose=True))
        else:
            agent = create_cot_agent(model_name=args.model, mode=args.mode)
            asyncio.run(run_agent_query(agent, prompt, verbose=True))


if __name__ == "__main__":
    main()

