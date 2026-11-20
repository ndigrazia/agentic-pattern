"""Main Orchestrator for Cross-Process Human-in-the-Loop Pattern using Google ADK.

Demonstrates an autonomous AI agent gating sensitive, high-impact operations
by requesting authorization from a human supervisor operating in another process.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import subprocess
import sys
import time
import uuid

from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
import nest_asyncio

from agent import cloud_operations_agent
from agent_process import run_agent_turn
from ipc_store import DEFAULT_DB_FILENAME, IPCAuthorizationStore
from supervisor_process import run_interactive_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("HITL.Main")

load_dotenv()


SCENARIOS = {
    "1": {
        "title": "Scenario 1: Autonomous Diagnostics (No Human Gate Needed)",
        "prompt": "What is the health and telemetry status of cluster prod-uscentral-01?",
        "auto_approve": None,
        "description": "Routine read-only operation executed autonomously by the agent without triggering gates.",
    },
    "2": {
        "title": "Scenario 2: Critical Cluster Reboot (Human Supervisor in Other Process Approves)",
        "prompt": "Please execute a rolling reboot of production cluster prod-uscentral-01 due to unresponsive nodes.",
        "auto_approve": True,
        "notes": "Supervisor verified on-call alert and approved rolling reboot for prod-uscentral-01.",
        "description": "High-impact infrastructure reboot requiring human supervisor sign-off in external process.",
    },
    "3": {
        "title": "Scenario 3: Budget Transfer (Human Supervisor in Other Process Rejects)",
        "prompt": "Transfer $250,000 from Marketing to AI Research to cover emergency GPU cloud cluster training.",
        "auto_approve": False,
        "notes": "Rejected by Financial Controller: Reallocation exceeds Q4 threshold ($50k). Requires RFC board approval.",
        "description": "High-value financial transfer rejected by supervisor; agent handles rejection gracefully.",
    },
}


async def execute_scenario(
    scenario_key: str,
    ipc_store: IPCAuthorizationStore,
    interactive_supervisor: bool = False,
    delay_seconds: float = 1.0,
) -> None:
    """Executes a scenario demonstrating the cross-process HITL flow."""
    sc = SCENARIOS[scenario_key]
    print("\n" + "#" * 80)
    print(f"🎬 {sc['title']}")
    print(f"   Description: {sc['description']}")
    print("#" * 80)

    sup_process = None
    if sc["auto_approve"] is not None and not interactive_supervisor:
        flag = "--auto-approve" if sc["auto_approve"] else "--auto-reject"
        cmd = [
            sys.executable,
            "supervisor_process.py",
            "--db-path",
            str(ipc_store.db_path),
            flag,
            "--delay",
            str(delay_seconds),
            "--notes",
            sc.get("notes", ""),
        ]
        sup_process = subprocess.Popen(cmd)
        time.sleep(0.3)

    try:
        runner = InMemoryRunner(cloud_operations_agent)
        user_id = "cloud_admin_sarah"
        session_id = str(uuid.uuid4())
        await runner.session_service.create_session(
            app_name=runner.app_name, user_id=user_id, session_id=session_id
        )

        await run_agent_turn(
            runner=runner,
            user_id=user_id,
            session_id=session_id,
            user_prompt=sc["prompt"],
            ipc_store=ipc_store,
            timeout_seconds=60.0,
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
        help="Execution role: 'demo' (spawns separate supervisor process automatically), 'agent' (runs only agent process), or 'supervisor' (runs supervisor process)",
    )
    parser.add_argument(
        "--scenario",
        choices=["1", "2", "3", "all"],
        default="2",
        help="Scenario to run: 1 (Autonomous), 2 (Reboot Approved), 3 (Transfer Rejected), or 'all' (default: 2)",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="In agent mode, waits for human supervisor via separate terminal or prompt",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Simulated supervisor review delay in demo mode (default: 1.0s)",
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="Custom SQLite IPC path (defaults to hitl_auth_requests.db)",
    )
    return parser.parse_args()


async def async_main(args: argparse.Namespace):
    ipc_store = IPCAuthorizationStore(args.db_path)

    if args.role == "supervisor":
        run_interactive_loop(ipc_store)
        return

    if args.role == "agent":
        print("\n🚀 [Agent Process Mode]")
        print("   The agent process will pause on critical tools and await authorization")
        print("   from a Human Supervisor operating in ANOTHER PROCESS.")
        print(f"   Ensure 'python supervisor_process.py' is running in another terminal!\n")
        runner = InMemoryRunner(cloud_operations_agent)
        user_id = "cloud_operator"
        session_id = str(uuid.uuid4())
        await runner.session_service.create_session(
            app_name=runner.app_name, user_id=user_id, session_id=session_id
        )
        sc = SCENARIOS.get(args.scenario, SCENARIOS["2"])
        await run_agent_turn(
            runner=runner,
            user_id=user_id,
            session_id=session_id,
            user_prompt=sc["prompt"],
            ipc_store=ipc_store,
            timeout_seconds=120.0,
        )
        return

    # Default: "demo" role
    scenarios_to_run = ["1", "2", "3"] if args.scenario == "all" else [args.scenario]
    for s_id in scenarios_to_run:
        await execute_scenario(
            scenario_key=s_id,
            ipc_store=ipc_store,
            interactive_supervisor=args.interactive,
            delay_seconds=args.delay,
        )


def main():
    args = parse_arguments()
    nest_asyncio.apply()
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()


