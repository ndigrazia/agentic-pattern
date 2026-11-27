"""CLI entrypoint and demonstration runner for Program-Aided Language Models (PALM)."""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

base_dir = Path(__file__).resolve().parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from google.genai import types

from palm_agent import create_palm_system, get_default_model, root_agent

load_dotenv()

BENCHMARKS = [
    {
        "category": "High-Precision Arithmetic",
        "question": "A principal of $15,000 grows at 6.5% interest compounded monthly. Compute balance and interest after 7 years.",
    },
    {
        "category": "Number Theory / Combinatorics",
        "question": "Write and run Python code to find all prime numbers between 500 and 550 and calculate their sum.",
    },
    {
        "category": "Search & Compute",
        "question": "Search for the height of Burj Khalifa in meters, then write Python code to convert it to feet.",
    },
]


async def run_agent_query(
    agent_or_system: Any,
    prompt: str,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Runs a query through RootAgent using InMemoryRunner."""
    runner = InMemoryRunner(agent_or_system)
    user_id = "user_palm"
    session_id = f"session_{uuid.uuid4().hex[:8]}"

    await runner.session_service.create_session(
        app_name=runner.app_name, user_id=user_id, session_id=session_id
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
                        print(f"\n[{event.author} ⚙️ Delegating]: {call.name}")
                        if call.args:
                            for k, v in call.args.items():
                                print(f"   ↳ {k}: {str(v)[:150]}")
                elif getattr(part, "function_response", None):
                    resp = part.function_response
                    if verbose:
                        resp_str = str(resp.response)[:200]
                        print(f"[{event.author} 💻 Tool Result]: {resp_str}")
                elif getattr(part, "text", None):
                    event_logs.append({"author": event.author, "text": part.text})
                    if verbose and not event.is_final_response():
                        print(f"\n[{event.author}]: {part.text}")

        if event.is_final_response() and event.content:
            if hasattr(event.content, "text") and event.content.text:
                response_text = event.content.text
            elif event.content.parts:
                response_text = "".join(p.text for p in event.content.parts if p.text)

    elapsed_time = time.perf_counter() - start_time
    final_output = response_text or "".join(l["text"] for l in event_logs)
    if verbose:
        print(f"\n🎯 [Final Answer]:\n{final_output}")
        print(f"\n⏱️ Elapsed Time: {elapsed_time:.2f}s")

    return {
        "response": final_output,
        "events": event_logs,
        "elapsed_seconds": round(elapsed_time, 2),
    }


async def run_benchmark(model_name: Optional[str] = None) -> None:
    """Runs a multi-domain PALM benchmark suite."""
    print("\n" + "=" * 70 + "\n🚀 RUNNING PALM BENCHMARK SUITE\n" + "=" * 70)
    agent = create_palm_system(model_name=model_name)
    for idx, item in enumerate(BENCHMARKS, 1):
        print(f"\n[{idx}/{len(BENCHMARKS)}] {item['category']}: {item['question']}")
        print("-" * 60)
        res = await run_agent_query(agent, item["question"], verbose=True)
        print(f"Solved in {res['elapsed_seconds']}s\n" + "=" * 70)


async def run_interactive(model_name: Optional[str] = None) -> None:
    """Interactive REPL for PALM."""
    print(f"\n💬 Interactive PALM Agent (Model: {model_name or get_default_model()})")
    print("Type your question. Type 'exit' to quit.\n" + "=" * 70)
    agent = create_palm_system(model_name=model_name)
    while True:
        try:
            inp = input("\n🤔 Enter Question > ").strip()
            if not inp:
                continue
            if inp.lower() in ("exit", "quit"):
                break
            await run_agent_query(agent, inp, verbose=True)
        except (KeyboardInterrupt, EOFError):
            break


def main() -> None:
    parser = argparse.ArgumentParser(description="PALM Agent with Google ADK")
    parser.add_argument("-p", "--prompt", type=str, help="Question to solve")
    parser.add_argument("--model", type=str, default=None, help="Gemini model override")
    parser.add_argument("-b", "--benchmark", action="store_true", help="Run benchmarks")
    parser.add_argument("-i", "--interactive", action="store_true", help="Interactive REPL")
    args = parser.parse_args()

    if args.benchmark:
        asyncio.run(run_benchmark(model_name=args.model))
    elif args.interactive:
        asyncio.run(run_interactive(model_name=args.model))
    else:
        prompt = args.prompt or "Calculate 2^20 - 1 using Python and check if it is divisible by 31."
        print(f"\n💡 Running Program-Aided Language Model (PALM)\n❓ Prompt: {prompt}\n")
        agent = create_palm_system(model_name=args.model)
        asyncio.run(run_agent_query(agent, prompt, verbose=True))


if __name__ == "__main__":
    main()

