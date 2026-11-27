"""Unit and integration tests for Google ADK Web compatibility with PALM Agent."""

from __future__ import annotations

import importlib
from pathlib import Path
import subprocess
import sys
import time
import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.adk.agents import BaseAgent
from google.adk.cli.utils.agent_loader import AgentLoader


def test_package_exports_root_agent():
    """Verify palm_agent package exposes root_agent for ADK Web discovery."""
    mod = importlib.import_module("palm_agent")
    assert hasattr(mod, "root_agent"), "palm_agent package must export 'root_agent'"
    agent = getattr(mod, "root_agent")
    assert isinstance(agent, BaseAgent)
    assert agent.name == "RootAgent"


def test_agent_loader_discovery():
    """Verify ADK AgentLoader discovers palm_agent properly."""
    base_dir = str(Path(__file__).resolve().parent.parent)
    loader = AgentLoader(agents_dir=base_dir)
    discovered = loader.list_agents()
    assert "palm_agent" in discovered, f"Expected 'palm_agent' in {discovered}"
    loaded = loader.load_agent("palm_agent")
    assert loaded.name == "RootAgent"


def test_adk_web_live_server_endpoints():
    """Starts `adk web` on an ephemeral port and tests discovery and session endpoints."""
    base_dir = str(Path(__file__).resolve().parent.parent)
    port = 8899
    host = "127.0.0.1"

    cmd = [
        "uv",
        "run",
        "adk",
        "web",
        base_dir,
        f"--host={host}",
        f"--port={port}",
    ]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    base_url = f"http://{host}:{port}"
    server_ready = False

    try:
        # Wait up to 12s for server startup
        for _ in range(24):
            time.sleep(0.5)
            try:
                res = requests.get(f"{base_url}/list-apps", timeout=1.0)
                if res.status_code == 200:
                    server_ready = True
                    break
            except Exception:
                continue

        assert server_ready, "ADK Web server failed to start within timeout"

        # 1. Test /list-apps endpoint
        res = requests.get(f"{base_url}/list-apps", timeout=2.0)
        assert res.status_code == 200
        apps = res.json()
        assert "palm_agent" in apps, f"Expected palm_agent in {apps}"

        # 2. Test /apps/palm_agent/app-info
        info_res = requests.get(f"{base_url}/apps/palm_agent/app-info", timeout=2.0)
        assert info_res.status_code == 200

        # 3. Test creating a session via ADK Web API
        user_id = "test_web_user"
        sess_res = requests.post(
            f"{base_url}/apps/palm_agent/users/{user_id}/sessions",
            json={},
            timeout=5.0,
        )
        assert sess_res.status_code == 200
        session_data = sess_res.json()
        session_id = session_data["id"]
        assert session_id is not None

        # 4. Test running agent execution via ADK Web /run endpoint
        run_res = requests.post(
            f"{base_url}/run",
            json={
                "app_name": "palm_agent",
                "user_id": user_id,
                "session_id": session_id,
                "new_message": {
                    "role": "user",
                    "parts": [{"text": "Calculate 15 * 15 using Python CodeAgent."}],
                },
            },
            timeout=30.0,
        )
        assert run_res.status_code == 200
        events = run_res.json()
        assert len(events) > 0
        event_authors = [e.get("author") for e in events if "author" in e]
        assert "RootAgent" in event_authors

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            proc.kill()
