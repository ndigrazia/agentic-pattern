"""CLI entrypoint and demonstration runner for the Reasoning and Acting (ReAct) Pattern.

Supports:
- Zero-Shot and Few-Shot ReAct execution with interleaved Thought, Action, and Observation.
- Side-by-side comparison between Direct Answering (no tools) and ReAct Agent.
- Multi-step reasoning benchmark suite.
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

from react_agent import (
    create_direct_agent,
    create_react_agent,
    get_default_model,
)

load_dotenv()

BENCHMARK_PROMPTS = [
    {
        "category": "Multi-Hop Incident Triage & Telemetry",
        "question": (
            "Service 'auth-service' has an alert. Check its current memory utilization, "
            "verify if it exceeds the SLO warning threshold from documentation, "
            "look up the on-call engineer responsible, and check incident ticket INC-101."
        ),
    },
    {
        "category": "Financial KPI & Mathematical Growth",
        "question": (
            "From the FY2025 financial documentation, retrieve Q3 and Q4 cloud revenue. "
            "Calculate the quarter-over-quarter percentage growth rate, "
            "and check whether it exceeded the 15% benchmark target."
        ),
    },
    {
        "category": "Infrastructure Sizing & Discount Calculation",
        "question": (
            "Search for compute instance pricing for 'n2-standard-8'. "
            "If a 1-year Committed Use Discount (CUD) of 37% is applied to its monthly price (720 hours), "
            "calculate the discounted monthly cost and compare it with the standard monthly price of n2-standard-4."
        ),
    },
]


async def run_agent_query(
    agent: Any,
    prompt: str,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Runs a prompt through an ADK agent using InMemoryRunner, tracking thoughts and actions."""
    runner = InMemoryRunner(agent)
    user_id = "user_default"
    session_id = f"session_{uuid.uuid4().hex[:8]}"

    await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )

    message = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])

    event_logs: List[Dict[str, Any]] = []
    response_text_parts: List[str] = []
    start_time = time.perf_counter()

    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=message
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                # 1. Action invocation (tool call)
                if getattr(part, "function_call", None):
                    call = part.function_call
                    if verbose:
                        print(f"\n⚡ [{event.author} ⚙️ Action]: {call.name}({call.args})")
                    event_logs.append({
                        "type": "action",
                        "author": event.author,
                        "name": call.name,
                        "args": call.args,
                    })
                # 2. Observation returned from environment / tool
                elif getattr(part, "function_response", None):
                    resp = part.function_response
                    if verbose:
                        print(f"📥 [{event.author} 👁️ Observation]: {resp.response}")
                    event_logs.append({
                        "type": "observation",
                        "author": event.author,
                        "response": resp.response,
                    })
                # 3. Model thought or final answer
                elif getattr(part, "text", None):
                    txt = part.text
                    response_text_parts.append(txt)
                    event_logs.append({
                        "type": "thought_or_answer",
                        "author": event.author,
                        "text": txt,
                    })
                    if verbose:
                        print(f"\n🧠 [{event.author}]:\n{txt}")

    elapsed = round(time.perf_counter() - start_time, 2)
    full_response = "\n".join(response_text_parts)

    return {
        "full_text": full_response,
        "events": event_logs,
        "elapsed_seconds": elapsed,
    }


async def run_comparison(prompt: str, model_name: Optional[str] = None) -> None:
    """Runs Direct Answering vs ReAct Agent side-by-side to contrast reasoning and tool grounding."""
    print("\n" + "=" * 78)
    print("⚖️  SIDE-BY-SIDE COMPARISON: DIRECT ANSWERING vs. ReAct AGENT")
    print("=" * 78)
    print(f"❓ Prompt: {prompt}\n")

    direct_agent = create_direct_agent(model_name=model_name)
    react_agent = create_react_agent(model_name=model_name, mode="few-shot")

    print("\n--- 1. DIRECT AGENT (Parametric Memory Only, No Tools) ---")
    direct_res = await run_agent_query(direct_agent, prompt, verbose=True)
    print(f"⏱️ Direct Elapsed: {direct_res['elapsed_seconds']}s")

    print("\n" + "-" * 60)
    print("--- 2. ReAct AGENT (Interleaved Thought -> Action -> Observation) ---")
    react_res = await run_agent_query(react_agent, prompt, verbose=True)
    print(f"⏱️ ReAct Elapsed: {react_res['elapsed_seconds']}s")

    print("\n" + "=" * 78)
    print("📊 Comparison Summary")
    print(f"Direct Response Latency: {direct_res['elapsed_seconds']}s (Zero external tool verification)")
    react_actions = [e for e in react_res["events"] if e.get("type") == "action"]
    print(f"ReAct Response Latency:  {react_res['elapsed_seconds']}s ({len(react_actions)} verified tool actions)")
    print("Takeaway: ReAct grounds claims in verifiable observations and computes exact values.")
    print("=" * 78)


async def run_benchmark(model_name: Optional[str] = None) -> None:
    """Runs a multi-domain ReAct benchmark suite."""
    print("\n" + "=" * 78)
    print("🚀 RUNNING ReAct (REASONING & ACTING) BENCHMARK SUITE")
    print("=" * 78)

    agent = create_react_agent(model_name=model_name, mode="few-shot")

    for idx, item in enumerate(BENCHMARK_PROMPTS, 1):
        print(f"\n[Problem {idx}/{len(BENCHMARK_PROMPTS)}] Category: {item['category']}")
        print(f"Question: {item['question']}")
        print("-" * 60)
        res = await run_agent_query(agent, item["question"], verbose=True)
        actions = [e for e in res["events"] if e.get("type") == "action"]
        print(f"\n⏱️ Completed in {res['elapsed_seconds']}s with {len(actions)} tool action(s)\n")
        print("=" * 78)


async def run_interactive(model_name: Optional[str] = None, mode: str = "few-shot") -> None:
    """Interactive REPL for ReAct agent."""
    print("\n" + "=" * 78)
    print(f"💬 Interactive ReAct Agent (Mode: {mode}, Model: {model_name or get_default_model()})")
    print("Type your reasoning & tool-use question. Type 'exit' or 'quit' to end.")
    print("=" * 78 + "\n")

    agent = create_react_agent(model_name=model_name, mode=mode)

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
        description="Reasoning and Acting (ReAct) Agent with Google ADK"
    )
    parser.add_argument(
        "-p", "--prompt",
        type=str,
        help="Input query or multi-step question to solve with ReAct",
    )
    parser.add_argument(
        "-m", "--mode",
        type=str,
        choices=["few-shot", "zero-shot"],
        default="few-shot",
        help="ReAct prompt mode: few-shot or zero-shot (default: few-shot)",
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
        help="Compare Direct Answering vs ReAct Agent side-by-side",
    )
    parser.add_argument(
        "-b", "--benchmark",
        action="store_true",
        help="Run multi-domain reasoning and acting benchmark suite",
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
        print(f"\n💡 Running ReAct Agent [Mode: {args.mode}]")
        print(f"❓ Prompt: {prompt}\n")
        agent = create_react_agent(model_name=args.model, mode=args.mode)
        asyncio.run(run_agent_query(agent, prompt, verbose=True))


if __name__ == "__main__":
    main()

