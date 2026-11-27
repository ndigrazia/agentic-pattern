"""CLI entrypoint and demonstration runner for the Self-Correction Reasoning Pattern.

Demonstrates:
- Systematic 5-step self-correction process on initial drafts.
- GreenTech Gadgets social media post launch benchmark (from prompt specifications).
- Two-stage multi-agent workflow (DraftWriter -> SelfCorrectionCritic).
- Benchmark suite across diverse content domains.
- Interactive REPL for real-time draft critique and correction.
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

from self_correction_agent import (
    create_self_correction_agent,
    create_self_correction_workflow,
    get_default_model,
)

load_dotenv()

DEFAULT_PROMPT_CASE = {
    "title": "GreenTech Gadgets Social Media Post Launch",
    "requirements": (
        "Write a short, engaging social media post (max 150 characters) "
        "announcing a new eco-friendly product line: 'GreenTech Gadgets'."
    ),
    "draft": (
        "We have new products. They are green and techy. Buy GreenTech Gadgets now!"
    ),
}

BENCHMARK_CASES = [
    DEFAULT_PROMPT_CASE,
    {
        "title": "Database Outage Incident Status Update",
        "requirements": (
            "Write a professional customer status update email regarding a 45-minute database outage. "
            "Requirements: empathetic tone, explain root cause (memory exhaustion on primary cluster), "
            "confirm full data integrity with zero loss, and outline prevention actions."
        ),
        "draft": (
            "The database crashed because of memory problems. It took 45 minutes to fix. "
            "No data was lost. Don't worry, we are looking into it."
        ),
    },
    {
        "title": "Security Advisory Notice",
        "requirements": (
            "Write a concise, urgent security advisory to developers requiring immediate rotation "
            "of API keys exposed in a public repository commit. "
            "Requirements: clear severity rating (HIGH), exact steps to revoke old key and generate a new key, "
            "and a deadline of 2 hours."
        ),
        "draft": (
            "Hey team, someone leaked a key on GitHub. Please make a new one when you get time today."
        ),
    },
]


def format_user_query(requirements: str, draft: str) -> str:
    """Combines requirements and draft into a structured user prompt."""
    return (
        f"**Original Prompt/Requirements:** \"{requirements}\"\n\n"
        f"**Initial Draft (Content to be corrected):**\n\"{draft}\"\n\n"
        f"Please apply your systematic 5-step self-correction process to review, critique, "
        f"and generate the refined content."
    )

async def run_agent_query(
    agent_or_workflow: Any,
    query_text: str,
    verbose: bool = True,
    initial_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Runs a query through an ADK agent or workflow using InMemoryRunner."""
    runner = InMemoryRunner(agent_or_workflow)
    user_id = "user_default"
    session_id = f"session_{uuid.uuid4().hex[:8]}"

    await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
        state=initial_state or {},
    )

    message = types.Content(role="user", parts=[types.Part.from_text(text=query_text)])

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


async def run_benchmark(model_name: Optional[str] = None) -> None:
    """Runs a multi-case self-correction benchmark suite."""
    print("\n" + "=" * 78)
    print("🚀 RUNNING SELF-CORRECTION BENCHMARK SUITE")
    print("=" * 78)

    agent = create_self_correction_agent(model_name=model_name, mode="few-shot")

    for idx, case in enumerate(BENCHMARK_CASES, 1):
        print(f"\n[Case {idx}/{len(BENCHMARK_CASES)}] {case['title']}")
        print(f"Requirements: {case['requirements']}")
        print(f"Initial Draft: {case['draft']}")
        print("-" * 60)
        query = format_user_query(case["requirements"], case["draft"])
        res = await run_agent_query(agent, query, verbose=True)
        print(f"⏱️ Evaluated and corrected in {res['elapsed_seconds']}s\n")
        print("=" * 78)


async def run_interactive(model_name: Optional[str] = None) -> None:
    """Interactive REPL for Self-Correction reasoning."""
    print("\n" + "=" * 78)
    print(f"💬 Interactive Self-Correction Agent (Model: {model_name or get_default_model()})")
    print("Provide initial requirements and draft content. Type 'exit' to quit.")
    print("=" * 78 + "\n")

    agent = create_self_correction_agent(model_name=model_name, mode="few-shot")

    while True:
        try:
            req = input("\n📋 Enter Requirements (or 'exit') > ").strip()
            if not req or req.lower() in ("exit", "quit"):
                break
            draft = input("📝 Enter Initial Draft to correct > ").strip()
            if not draft:
                print("Draft cannot be empty.")
                continue

            query = format_user_query(req, draft)
            await run_agent_query(agent, query, verbose=True)
        except (KeyboardInterrupt, EOFError):
            print("\nSession ended.")
            break


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Self-Correction Reasoning Agent with Google ADK"
    )
    parser.add_argument(
        "-r", "--requirements",
        type=str,
        default=DEFAULT_PROMPT_CASE["requirements"],
        help="Initial requirements or intent specification",
    )
    parser.add_argument(
        "-d", "--draft",
        type=str,
        default=DEFAULT_PROMPT_CASE["draft"],
        help="Initial draft content to be corrected",
    )
    parser.add_argument(
        "-m", "--mode",
        type=str,
        choices=["agent", "workflow"],
        default="agent",
        help="Execution mode: standalone self-correction 'agent' or two-stage 'workflow'",
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
        help="Compare Standalone Agent vs Multi-Agent Workflow side-by-side",
    )
    parser.add_argument(
        "-b", "--benchmark",
        action="store_true",
        help="Run multi-case self-correction benchmark suite",
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Start an interactive REPL session",
    )

    args = parser.parse_args()

    if args.compare:
        from compare import compare_alternatives
        asyncio.run(compare_alternatives(args.requirements, args.draft, model_name=args.model))
    elif args.benchmark:
        asyncio.run(run_benchmark(model_name=args.model))
    elif args.interactive:
        asyncio.run(run_interactive(model_name=args.model))
    else:
        print("\n" + "=" * 78)
        print("🎯 Self-Correction Agent Demonstration")
        print("=" * 78)
        print(f"📋 Requirements: {args.requirements}")
        print(f"📝 Initial Draft: {args.draft}")
        print("=" * 78 + "\n")

        if args.mode == "workflow":
            workflow = create_self_correction_workflow(model_name=args.model)
            query = (
                f"Requirements: {args.requirements}\n"
                f"Please generate an initial draft, then critically review and self-correct it."
            )
            initial_state = {"original_requirements": args.requirements}
            asyncio.run(run_agent_query(workflow, query, verbose=True, initial_state=initial_state))
        else:
            agent = create_self_correction_agent(model_name=args.model, mode="few-shot")
            query = format_user_query(args.requirements, args.draft)
            asyncio.run(run_agent_query(agent, query, verbose=True))


if __name__ == "__main__":
    main()


