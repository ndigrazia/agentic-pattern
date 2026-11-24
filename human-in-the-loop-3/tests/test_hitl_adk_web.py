"""Tests for Google ADK Cross-Process Human-in-the-Loop Pattern with ADK Web."""

import asyncio
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from ipc_store import IPCAuthorizationStore
from hitl_agent.agent import root_agent
from google.adk.runners import InMemoryRunner
from google.adk.cli.fast_api import get_fast_api_app


@pytest.fixture
def temp_ipc_store():
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        store = IPCAuthorizationStore(tmp.name)
        yield store


def test_ipc_store_crud(temp_ipc_store):
    store = temp_ipc_store
    req = store.create_request(
        session_id="sess_123",
        user_id="user_test",
        function_call_id="call_abc",
        tool_name="reboot_production_cluster",
        tool_args={"cluster_id": "c1"},
        agent_pid=1111,
    )
    assert req.request_id.startswith("AUTH-")
    assert req.status == "PENDING"
    assert req.tool_name == "reboot_production_cluster"

    fetched = store.get_request(req.request_id)
    assert fetched is not None
    assert fetched.request_id == req.request_id
    assert fetched.tool_args == {"cluster_id": "c1"}

    pending = store.get_pending_requests()
    assert len(pending) == 1

    resolved = store.resolve_request(
        request_id=req.request_id,
        approved=True,
        notes="Verified ok",
        supervisor_pid=2222,
    )
    assert resolved.status == "APPROVED"
    assert resolved.supervisor_notes == "Verified ok"
    assert resolved.supervisor_pid == 2222
    assert len(store.get_pending_requests()) == 0


def test_ipc_store_rejection(temp_ipc_store):
    store = temp_ipc_store
    req = store.create_request(
        session_id="sess_456",
        user_id="user_test2",
        function_call_id="call_def",
        tool_name="transfer_budget_funds",
        tool_args={"amount_usd": 100000},
        agent_pid=3333,
    )
    resolved = store.resolve_request(
        request_id=req.request_id,
        approved=False,
        notes="Exceeds quarterly limit",
        supervisor_pid=4444,
    )
    assert resolved.status == "REJECTED"
    assert resolved.supervisor_notes == "Exceeds quarterly limit"


def test_ipc_store_wait_decision(temp_ipc_store):
    async def _run():
        store = temp_ipc_store
        req = store.create_request(
            session_id="sess_async",
            user_id="user_async",
            function_call_id="call_async",
            tool_name="reboot_production_cluster",
            tool_args={"cluster_id": "c2"},
            agent_pid=os.getpid(),
        )

        async def supervisor_task():
            await asyncio.sleep(0.2)
            store.resolve_request(req.request_id, approved=True, notes="Async authorized", supervisor_pid=9999)

        asyncio.create_task(supervisor_task())
        decision = await store.wait_for_decision(req.request_id, timeout_seconds=2.0)
        assert decision.status == "APPROVED"
def test_ipc_store_timeout(temp_ipc_store):
    async def _run():
        store = temp_ipc_store
        req = store.create_request(
            session_id="sess_timeout",
            user_id="user_to",
            function_call_id="call_to",
            tool_name="test_tool",
            tool_args={},
            agent_pid=os.getpid(),
        )
        with pytest.raises(TimeoutError):
            await store.wait_for_decision(req.request_id, timeout_seconds=0.3, poll_interval=0.1)

    asyncio.run(_run())


def test_adk_web_app_discovery_and_endpoints():
    app = get_fast_api_app(
        agents_dir=str(Path(__file__).parent.parent),
        web=True,
    )
    client = TestClient(app)

    # 1. Check list-apps
    resp = client.get("/list-apps")
    assert resp.status_code == 200
    apps = resp.json()
    assert "hitl_agent" in apps

    # 2. Check app-info
    info_resp = client.get("/apps/hitl_agent/app-info")
    assert info_resp.status_code == 200
    info = info_resp.json()
    assert info["name"] == "hitl_agent"
    assert "reboot_production_cluster" in str(info)
    assert "transfer_budget_funds" in str(info)


def test_adk_web_cross_process_flow(temp_ipc_store):
    async def _run():
        store = temp_ipc_store
        app = get_fast_api_app(
            agents_dir=str(Path(__file__).parent.parent),
            web=True,
        )

        sup_proc = subprocess.Popen([
            sys.executable,
            str(Path(__file__).parent.parent / "supervisor_process.py"),
            "--db-path",
            str(store.db_path),
            "--auto-approve",
            "--delay",
            "0.3",
            "--max-decisions",
            "1",
            "--notes",
            "Approved via Pytest ADK Web Client",
        ])

        try:
            # Override store in hitl_agent for this test
            import hitl_agent.agent as ag_mod
            ag_mod._SHARED_STORE = store

            client = TestClient(app)
            user_id = "test_sre"
            session_id = f"sess-{uuid.uuid4().hex[:6]}"

            # Create session
            create_resp = client.post(f"/apps/hitl_agent/users/{user_id}/sessions/{session_id}", json={})
            assert create_resp.status_code in (200, 201)

            # Post run request
            run_payload = {
                "appName": "hitl_agent",
                "userId": user_id,
                "sessionId": session_id,
                "newMessage": {
                    "role": "user",
                    "parts": [{"text": "Please execute a rolling reboot of production cluster prod-uscentral-01 due to unresponsive nodes."}],
                },
            }
            run_resp = client.post("/run", json=run_payload)
            assert run_resp.status_code == 200
            events = run_resp.json()

            # Verify events
            all_text = ""
            called_tools = []
            for ev in events:
                for part in ev.get("content", {}).get("parts", []):
                    if "functionCall" in part:
                        called_tools.append(part["functionCall"]["name"])
                    if "text" in part:
                        all_text += part["text"]

            assert "reboot_production_cluster" in called_tools
            assert "OP-REBOOT-" in all_text or "approved" in all_text.lower()
        finally:
            sup_proc.terminate()
            sup_proc.wait()

    asyncio.run(_run())

