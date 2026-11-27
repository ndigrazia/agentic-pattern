"""Unit tests for Google ADK Web compatibility, discovery, and HTTP server testing."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
import subprocess
import sys
import time
import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.adk.agents import BaseAgent, LlmAgent


def test_package_exports_root_agent():
    """Verify self_correction_agent package exposes root_agent for ADK Web discovery."""
    mod = importlib.import_module("self_correction_agent")
    assert hasattr(mod, "root_agent"), "self_correction_agent package must export 'root_agent'"

    agent = getattr(mod, "root_agent")
    assert isinstance(agent, BaseAgent), f"Expected BaseAgent, got {type(agent)}"
    assert agent.name == "self_correction_agent"


def test_root_agent_configuration():
    """Verify root_agent has correct prompt instructions, tools, and description."""
    from self_correction_agent.agent import root_agent

    assert isinstance(root_agent, LlmAgent)
    assert "Self-Correction Agent" in root_agent.description
    assert len(root_agent.tools) == 2
    tool_names = [t.name for t in root_agent.tools]
    assert "analyze_text_metrics" in tool_names
    assert "verify_constraint_checklist" in tool_names

    # Verify systematic 5-step instructions
    assert "1. **Understand Original Requirements:**" in root_agent.instruction
    assert "2. **Analyze Current Content:**" in root_agent.instruction
    assert "3. **Identify Discrepancies/Weaknesses:**" in root_agent.instruction
    assert "4. **Propose Specific Improvements:**" in root_agent.instruction
    assert "5. **Generate Revised Content:**" in root_agent.instruction
    assert "GreenTech Gadgets" in root_agent.instruction


def test_adk_web_live_server_discovery():
    """Starts `adk web` on an ephemeral port and tests HTTP discovery endpoints."""
    base_dir = str(Path(__file__).resolve().parent.parent)
    port = 8876
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
        # Wait up to 12 seconds for server startup
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
        assert "self_correction_agent" in apps, f"Expected self_correction_agent in {apps}"

        # 2. Test /apps/self_correction_agent/app-info
        info_res = requests.get(f"{base_url}/apps/self_correction_agent/app-info", timeout=2.0)
        assert info_res.status_code == 200
        info_data = info_res.json()
        assert "name" in info_data or "root_agent" in info_data or "description" in str(info_data)

        # 3. Test creating session via ADK Web API
        user_id = "test_web_user"
        sess_res = requests.post(
            f"{base_url}/apps/self_correction_agent/users/{user_id}/sessions",
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
                "app_name": "self_correction_agent",
                "user_id": user_id,
                "session_id": session_id,
                "new_message": {
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                "Original Prompt/Requirements: Write a short social post (max 150 chars) for GreenTech Gadgets\n"
                                "Initial Draft: We have new green tech products. Buy now!"
                            )
                        }
                    ],
                },
            },
            timeout=30.0,
        )
        assert run_res.status_code == 200
        events = run_res.json()
        assert len(events) > 0
        # Verify event authors contain self_correction_agent
        event_authors = [e.get("author") for e in events if "author" in e]
        assert "self_correction_agent" in event_authors

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            proc.kill()
