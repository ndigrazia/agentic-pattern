"""End-to-End Proof and Client Demonstration with live Google ADK Web server.

Spins up `adk web` on an available port, verifies application discovery,
and tests real-time query routing against `/run` for both Flash and Pro tiers.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional
import uuid

import httpx


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
                resp = await client.get(f"{base_url}/list-apps", timeout=1.0)
                if resp.status_code == 200:
                    return True
            except Exception:
                pass
            await asyncio.sleep(0.3)
    return False


async def execute_web_query(
    base_url: str,
    app_name: str,
    prompt: str,
    user_id: str = "web_user",
) -> Dict[str, Any]:
    """Creates a session and runs a query via ADK Web HTTP API."""
    session_id = f"sess-{uuid.uuid4().hex[:8]}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Create Session
        sess_resp = await client.post(
            f"{base_url}/apps/{app_name}/users/{user_id}/sessions/{session_id}",
            json={},
        )
        if sess_resp.status_code not in (200, 201):
            raise RuntimeError(f"Failed to create session on ADK Web: {sess_resp.status_code} {sess_resp.text}")

        # 2. Execute /run
        payload = {
            "appName": app_name,
            "userId": user_id,
            "sessionId": session_id,
            "newMessage": {
                "role": "user",
                "parts": [{"text": prompt}],
            },
        }

        t0 = time.perf_counter()
        run_resp = await client.post(f"{base_url}/run", json=payload)
        elapsed = round(time.perf_counter() - t0, 3)

        if run_resp.status_code != 200:
            raise RuntimeError(f"ADK Web /run failed: {run_resp.status_code} {run_resp.text}")

        events = run_resp.json()
        routing_info = ""
        final_answer = ""
        invoked_agents: List[str] = []

        for ev in events:
            author = ev.get("author", "unknown")
            if author not in invoked_agents:
                invoked_agents.append(author)
            content = ev.get("content", {})
            for part in content.get("parts", []):
                text = part.get("text", "")
                if "[Resource-Aware Optimizer]" in text:
                    routing_info = text
                elif author != "optimization_agent" and text:
                    final_answer += text

        return {
            "prompt": prompt,
            "routing_info": routing_info,
            "final_answer": final_answer.strip(),
            "invoked_agents": invoked_agents,
            "elapsed_seconds": elapsed,
            "session_id": session_id,
            "events_count": len(events),
        }

async def main() -> None:
    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    agents_dir = str(Path(__file__).resolve().parent)

    print("\n" + "=" * 75)
    print("🚀 PROOF: RESOURCE-AWARE OPTIMIZATION WITH GOOGLE ADK WEB")
    print(f"   Target Base URL:   {base_url}")
    print(f"   Agents Directory:  {agents_dir}")
    print("=" * 75)

    # Launch ADK Web server process
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
    print(f"📡 Spawning ADK Web server process (port {port})...")
    proc = subprocess.Popen(adk_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        healthy = await wait_for_server_healthy(base_url, timeout_seconds=15.0)
        if not healthy:
            stdout, stderr = proc.communicate(timeout=2.0)
            raise RuntimeError(f"ADK Web server failed to start!\nSTDOUT: {stdout.decode()}\nSTDERR: {stderr.decode()}")

        print(f"✅ ADK Web server is UP and HEALTHY (PID: {proc.pid}) at {base_url}")

        # Check /list-apps
        async with httpx.AsyncClient() as client:
            apps_resp = await client.get(f"{base_url}/list-apps")
            apps = apps_resp.json()
            print(f"📋 Discovered ADK Web Applications: {apps}")
            assert "optimization_agent" in apps, f"Expected 'optimization_agent' in {apps}"

        # -------------------------------------------------------------
        # Scenario 1: Lightweight Factual Query -> Flash Tier
        # -------------------------------------------------------------
        print("\n" + "#" * 75)
        print("🧪 TEST 1: LIGHTWEIGHT QUERY VIA ADK WEB (ROUTED TO FLASH)")
        print("#" * 75)
        query_1 = "What is the capital of Australia?"
        print(f"📥 User Query: '{query_1}'")

        res_1 = await execute_web_query(base_url, "optimization_agent", query_1)
        print(f"⚡ {res_1['routing_info']}")
        print(f"🤖 Response: {res_1['final_answer']}")
        print(f"⏱️  Duration: {res_1['elapsed_seconds']}s | Agents: {res_1['invoked_agents']}")

        assert "GeminiFlashAgent" in res_1["invoked_agents"], "Expected GeminiFlashAgent to be invoked!"
        assert "Canberra" in res_1["final_answer"], "Expected Canberra in response!"
        print("✅ TEST 1 PASSED: Successfully optimized to Flash tier via ADK Web.")

        # -------------------------------------------------------------
        # Scenario 2: Complex Architecture Query -> Pro Tier
        # -------------------------------------------------------------
        print("\n" + "#" * 75)
        print("🧪 TEST 2: COMPLEX ARCHITECTURAL QUERY VIA ADK WEB (ROUTED TO PRO)")
        print("#" * 75)
        query_2 = (
            "Design a distributed, fault-tolerant microservices architecture with Kafka, "
            "database sharding, and consensus protocols. Analyze trade-offs between consistency and latency."
        )
        print(f"📥 User Query: '{query_2}'")

        res_2 = await execute_web_query(base_url, "optimization_agent", query_2)
        print(f"🧠 {res_2['routing_info']}")
        preview_ans = res_2['final_answer'][:200] + ("..." if len(res_2['final_answer']) > 200 else "")
        print(f"🤖 Response Preview:\n{preview_ans}")
        print(f"⏱️  Duration: {res_2['elapsed_seconds']}s | Agents: {res_2['invoked_agents']}")

        assert "GeminiProAgent" in res_2["invoked_agents"], "Expected GeminiProAgent to be invoked!"
        assert len(res_2["final_answer"]) > 100, "Expected detailed response from Pro!"
        print("✅ TEST 2 PASSED: Successfully allocated high-capacity Pro tier via ADK Web.")

        print("\n" + "=" * 75)
        print("🎉 ALL PROOFS PASSED IN GOOGLE ADK WEB!")
        print(f"   Resource-Aware Optimization agent works seamlessly inside ADK Web.")
        print("=" * 75 + "\n")

    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5.0)


if __name__ == "__main__":
    asyncio.run(main())

