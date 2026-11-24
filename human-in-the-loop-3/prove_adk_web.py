"""Proof of Cross-Process Human-in-the-Loop in Google ADK Web.

Demonstrates and verifies that an agent served by `adk web` (FastAPI DevServer)
gates sensitive actions behind authorization from a human supervisor operating
in a separate OS process via SQLite IPC.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import uuid

import httpx

from ipc_store import DEFAULT_DB_FILENAME, IPCAuthorizationStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("HITL3.Proof")


def find_free_port() -> int:
    """Finds an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def wait_for_server_healthy(base_url: str, timeout_seconds: float = 20.0) -> bool:
    """Polls ADK Web server until healthy."""
    start = time.time()
    async with httpx.AsyncClient() as client:
        while time.time() - start < timeout_seconds:
            try:
                resp = await client.get(f"{base_url}/health", timeout=1.0)
                if resp.status_code == 200:
                    return True
            except Exception:
                pass
            await asyncio.sleep(0.3)
    return False


async def run_scenario_on_adk_web(
    base_url: str,
    app_name: str,
    user_prompt: str,
    user_id: str = "sarah_admin",
    session_id: Optional[str] = None,
) -> dict:
    """Creates a session and executes a run on the live ADK Web server."""
    session_id = session_id or f"sess-{uuid.uuid4().hex[:8]}"
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. Create session
        create_resp = await client.post(
            f"{base_url}/apps/{app_name}/users/{user_id}/sessions/{session_id}",
            json={},
        )
        if create_resp.status_code not in (200, 201):
            raise RuntimeError(f"Failed to create session on ADK Web: {create_resp.status_code} {create_resp.text}")

        # 2. Execute /run
        run_payload = {
            "appName": app_name,
            "userId": user_id,
            "sessionId": session_id,
            "newMessage": {
                "role": "user",
                "parts": [{"text": user_prompt}],
            },
        }

        print(f"\n🌐 [HTTP Request -> ADK Web ({base_url}/run)]")
        print(f"   App Name:   {app_name}")
        print(f"   User:       {user_id} | Session: {session_id}")
        print(f"   Prompt:     \"{user_prompt}\"")
        print("⏳ ADK Web is processing (will dispatch authorization to external process if gated)...")

        resp = await client.post(f"{base_url}/run", json=run_payload)
        if resp.status_code != 200:
            raise RuntimeError(f"ADK Web /run failed: {resp.status_code} {resp.text}")

        events = resp.json()
        final_text = ""
        tool_calls = []
        tool_responses = []

        for ev in events:
            content = ev.get("content", {})
            for part in content.get("parts", []):
                if "functionCall" in part:
                    fc = part["functionCall"]
                    tool_calls.append(fc)
                    print(f"⚙️  [ADK Web Tool Call]: {fc.get('name')}({fc.get('args')})")
                elif "functionResponse" in part:
                    fr = part["functionResponse"]
                    tool_responses.append(fr)
                    print(f"📥 [ADK Web Tool Response]: {fr.get('name')} -> {fr.get('response')}")
                elif "text" in part:
                    final_text += part["text"]

        print(f"\n🤖 [ADK Web Response to User]:\n{final_text.strip()}\n")
        return {
            "session_id": session_id,
            "events": events,
            "tool_calls": tool_calls,
            "tool_responses": tool_responses,
            "final_text": final_text,
        }


async def run_adk_web_proof() -> None:
    """End-to-end proof of cross-process HITL running against the live ADK Web server."""
    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    agents_dir = str(Path(__file__).parent)
    ipc_store = IPCAuthorizationStore(Path(__file__).parent / DEFAULT_DB_FILENAME)

    print("\n" + "=" * 80)
    print("🚀 STARTING PROOF: CROSS-PROCESS HITL WITH GOOGLE ADK WEB")
    print(f"   ADK Web Server URL:    {base_url}")
    print(f"   Agents Directory:      {agents_dir}")
    print(f"   SQLite IPC Store:      {ipc_store.db_path}")
    print("=" * 80)

    # Launch ADK Web server in background process
    adk_cmd = [
        sys.executable,
        "-m",
        "google.adk.cli",
        "web",
        agents_dir,
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--no-reload",
    ]
    print(f"📡 Spawning ADK Web server process: {' '.join(adk_cmd)}")
    adk_proc = subprocess.Popen(adk_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        # Wait for healthy
        healthy = await wait_for_server_healthy(base_url, timeout_seconds=20.0)
        if not healthy:
            stdout, stderr = adk_proc.communicate(timeout=2.0)
            raise RuntimeError(f"ADK Web server failed to start on {base_url}!\nSTDOUT: {stdout}\nSTDERR: {stderr}")

        print(f"✅ ADK Web server is UP and HEALTHY (PID: {adk_proc.pid}) at {base_url}")

        # Check list-apps
        async with httpx.AsyncClient() as client:
            apps_resp = await client.get(f"{base_url}/list-apps")
            apps = apps_resp.json()
            print(f"📋 Discovered ADK Web applications: {apps}")
            assert "hitl_agent" in apps, f"Expected 'hitl_agent' in {apps}"

        # --------------------------------------------------------------------
        # TEST 1: Critical Reboot -> Approved by Human Supervisor in OTHER process
        # --------------------------------------------------------------------
        print("\n" + "#" * 80)
        print("🧪 PROOF TEST 1: CRITICAL CLUSTER REBOOT (EXTERNAL SUPERVISOR APPROVES)")
        print("#" * 80)

        # Spawn supervisor in separate process
        sup_cmd_1 = [
            sys.executable,
            str(Path(__file__).parent / "supervisor_process.py"),
            "--db-path",
            str(ipc_store.db_path),
            "--auto-approve",
            "--delay",
            "1.2",
            "--max-decisions",
            "1",
            "--notes",
            "Verified by SRE On-Call (Process B): 4 nodes unresponsive. Rolling reboot approved.",
        ]
        sup_proc_1 = subprocess.Popen(sup_cmd_1)
        print(f"👤 Human Supervisor spawned in separate OS process (PID: {sup_proc_1.pid})")

        try:
            res_1 = await run_scenario_on_adk_web(
                base_url=base_url,
                app_name="hitl_agent",
                user_prompt="Please execute a rolling reboot of production cluster prod-uscentral-01 due to unresponsive nodes.",
            )
            sup_proc_1.wait(timeout=10.0)
            assert any(fc.get("name") == "reboot_production_cluster" for fc in res_1["tool_calls"]), "reboot_production_cluster was not called!"
            assert "OP-REBOOT-" in res_1["final_text"] or "approved" in res_1["final_text"].lower(), "Expected approval in response!"
            print(f"✅ PROOF 1 PASSED: Agent in ADK Web (PID: {adk_proc.pid}) gated on Supervisor (PID: {sup_proc_1.pid}) and completed reboot!")
        finally:
            if sup_proc_1.poll() is None:
                sup_proc_1.terminate()
                sup_proc_1.wait()

        # --------------------------------------------------------------------
        # TEST 2: Budget Transfer -> Rejected by Human Supervisor in OTHER process
        # --------------------------------------------------------------------
        print("\n" + "#" * 80)
        print("🧪 PROOF TEST 2: BUDGET TRANSFER (EXTERNAL SUPERVISOR REJECTS)")
        print("#" * 80)

        sup_cmd_2 = [
            sys.executable,
            str(Path(__file__).parent / "supervisor_process.py"),
            "--db-path",
            str(ipc_store.db_path),
            "--auto-reject",
            "--delay",
            "1.2",
            "--max-decisions",
            "1",
            "--notes",
            "Rejected by Financial Controller: Reallocation exceeds $50k discretionary ceiling.",
        ]
        sup_proc_2 = subprocess.Popen(sup_cmd_2)
        print(f"👤 Human Supervisor spawned in separate OS process (PID: {sup_proc_2.pid})")

        try:
            res_2 = await run_scenario_on_adk_web(
                base_url=base_url,
                app_name="hitl_agent",
                user_prompt="Transfer $250,000 from Marketing to AI Research to cover emergency GPU cloud cluster training.",
            )
            sup_proc_2.wait(timeout=10.0)
            assert any(fc.get("name") == "transfer_budget_funds" for fc in res_2["tool_calls"]), "transfer_budget_funds was not called!"
            assert "reject" in res_2["final_text"].lower() or "declined" in res_2["final_text"].lower(), "Expected rejection explanation in response!"
            print(f"✅ PROOF 2 PASSED: Agent in ADK Web (PID: {adk_proc.pid}) gated on Supervisor (PID: {sup_proc_2.pid}) and handled rejection gracefully!")
        finally:
            if sup_proc_2.poll() is None:
                sup_proc_2.terminate()
                sup_proc_2.wait()

        print("\n" + "=" * 80)
        print("🎉 ALL PROOFS PASSED IN ADK WEB!")
        print("   Cross-process HITL authorization demonstrated successfully with live ADK Web server.")
        print("=" * 80 + "\n")

    finally:
        if adk_proc.poll() is None:
            adk_proc.terminate()
            adk_proc.wait()


def main() -> None:
    asyncio.run(run_adk_web_proof())


if __name__ == "__main__":
    main()

