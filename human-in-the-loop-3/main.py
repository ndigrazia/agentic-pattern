"""Main Orchestrator for Cross-Process Human-in-the-Loop Pattern with Google ADK & Web UI.

Demonstrates an autonomous AI agent gating sensitive operations by requesting
authorization from a human supervisor operating in another process via IPC,
fully compatible with `adk web`.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from google.genai import types

from hitl_agent.agent import root_agent
from ipc_store import DEFAULT_DB_FILENAME, IPCAuthorizationStore
from supervisor_process import run_interactive_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("HITL3.Main")

load_dotenv()

SCENARIOS = {
    "1": {
        "title": "Scenario 1: Autonomous Telemetry & Diagnostics (No Gate Needed)",
        "prompt": "What is the health and telemetry status of cluster prod-uscentral-01?",
        "auto_approve": None,
        "description": "Routine read-only operation executed autonomously by the agent without triggering gates.",
    },
    "2": {
        "title": "Scenario 2: Critical Cluster Reboot (Human Supervisor in Other Process Approves)",
        "prompt": "Please execute a rolling reboot of production cluster prod-uscentral-01 due to unresponsive nodes.",
        "auto_approve": True,
        "notes": "Verified by Site Reliability Engineer: On-call alert confirmed 4 degraded nodes. Reboot approved.",
        "description": "High-impact infrastructure reboot requiring human supervisor sign-off in external process.",
    },
    "3": {
        "title": "Scenario 3: Budget Transfer (Human Supervisor in Other Process Rejects)",
        "prompt": "Transfer $250,000 from Marketing to AI Research to cover emergency GPU cloud cluster training.",
        "auto_approve": False,
        "notes": "Rejected by Financial Controller: Reallocation exceeds Q4 threshold ($50k). Requires RFC board approval.",
        "description": "High-value financial transfer rejected by supervisor in external console; agent handles rejection gracefully.",
    },
}


async def run_single_agent_turn(runner: InMemoryRunner, user_prompt: str, user_id: str, session_id: str) -> str:
    """Executes a single turn using the Google ADK runner."""
    print(f"\n💬 [User Prompt]: \"{user_prompt}\"")
    print(f"🤖 [Agent Process (PID: {os.getpid()})]: Executing turn via Google ADK...")

    initial_msg = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_prompt)],
    )

    final_response_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=initial_msg,
    ):
        if not event.content or not event.content.parts:
            continue
        for part in event.content.parts:
            if part.function_call:
                fc = part.function_call
                print(f"⚙️  [Agent Tool Call]: {fc.name}({fc.args})")
            elif part.function_response:
                fr = part.function_response
                print(f"📥 [Tool Response Received]: '{fr.name}' -> {fr.response}")
            elif part.text:
                final_response_text += part.text

    print(f"\n🤖 [Agent Final Answer]:\n{final_response_text.strip()}\n")
    return final_response_text

async def execute_scenario(
    scenario_key: str,
    ipc_store: IPCAuthorizationStore,
    interactive_supervisor: bool = False,
    delay_seconds: float = 1.0,
) -> None:
    sc = SCENARIOS[scenario_key]
    print("\n" + "#" * 80)
    print(f"🎬 {sc['title']}")
    print(f"   Description: {sc['description']}")
    print("#" * 80)

    user_id = "cloud_admin_sarah"
    session_id = str(uuid.uuid4())

    sup_process = None
    if sc["auto_approve"] is not None and not interactive_supervisor:
        flag = "--auto-approve" if sc["auto_approve"] else "--auto-reject"
        cmd = [
            sys.executable,
            str(Path(__file__).parent / "supervisor_process.py"),
            "--db-path",
            str(ipc_store.db_path),
            flag,
            "--delay",
            str(delay_seconds),
            "--notes",
            sc.get("notes", ""),
        ]
        sup_process = subprocess.Popen(cmd)
        time.sleep(0.4)

    try:
        runner = InMemoryRunner(root_agent)
        await runner.session_service.create_session(
            app_name=runner.app_name, user_id=user_id, session_id=session_id
        )

        await run_single_agent_turn(
            runner=runner,
            user_prompt=sc["prompt"],
            user_id=user_id,
            session_id=session_id,
        )
    finally:
        if sup_process:
            sup_process.terminate()
            sup_process.wait()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Google ADK Cross-Process Human-in-the-Loop Pattern")
    parser.add_argument(
        "--role",
        choices=["demo", "agent", "supervisor"],
        default="demo",
        help="Execution role: 'demo' (spawns separate supervisor process automatically), 'agent' (runs agent turn), 'supervisor' (runs supervisor process)",
    )
    parser.add_argument(
        "--scenario",
        choices=["1", "2", "3", "all"],
        default="2",
        help="Scenario to run: 1 (Autonomous), 2 (Critical Reboot - Approved), 3 (Transfer - Rejected), all",
    )
    parser.add_argument(
        "--prove-adk-web",
        action="store_true",
        help="Run end-to-end verification through the live adk web server and external supervisor process",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Simulated human review delay in seconds (demo mode)",
    )
    return parser.parse_args()


async def async_main() -> None:
    args = parse_arguments()
    ipc_store = IPCAuthorizationStore()

    if args.prove_adk_web:
        from prove_adk_web import run_adk_web_proof
        await run_adk_web_proof()
        return

    if args.role == "supervisor":
        run_interactive_loop(ipc_store)
        return

    if args.scenario == "all":
        for sk in ["1", "2", "3"]:
            await execute_scenario(
                scenario_key=sk,
                ipc_store=ipc_store,
                interactive_supervisor=(args.role == "agent"),
                delay_seconds=args.delay,
            )
            await asyncio.sleep(1.0)
    else:
        await execute_scenario(
            scenario_key=args.scenario,
            ipc_store=ipc_store,
            interactive_supervisor=(args.role == "agent"),
            delay_seconds=args.delay,
        )


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

