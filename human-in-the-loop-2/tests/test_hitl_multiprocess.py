"""Tests for Google ADK Cross-Process Human-in-the-Loop Pattern."""

import asyncio
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid
import pytest

from ipc_store import IPCAuthorizationStore
from agent import cloud_operations_agent
from agent_process import run_agent_turn
from google.adk.runners import InMemoryRunner


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
        assert decision.supervisor_pid == 9999

    asyncio.run(_run())


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


def test_cross_process_agent_turn_approved(temp_ipc_store):
    async def _run():
        store = temp_ipc_store
        sup_proc = subprocess.Popen([
            sys.executable,
            str(Path(__file__).parent.parent / "supervisor_process.py"),
            "--db-path",
            str(store.db_path),
            "--auto-approve",
            "--delay",
            "0.3",
            "--notes",
            "Approved via pytest background process",
        ])

        try:
            runner = InMemoryRunner(cloud_operations_agent)
            user_id = "test_user_p1"
            session_id = str(uuid.uuid4())
            await runner.session_service.create_session(
                app_name=runner.app_name, user_id=user_id, session_id=session_id
            )

            res = await run_agent_turn(
                runner=runner,
                user_id=user_id,
                session_id=session_id,
                user_prompt="Please restart production cluster k8s-prod-uswest-1 due to degraded nodes.",
                ipc_store=store,
                timeout_seconds=30.0,
            )
            assert res["status"] == "success"
            assert res["pending_tool"] == "reboot_production_cluster"
            assert res["auth_request"]["status"] == "APPROVED"
            assert res["auth_request"]["supervisor_pid"] == sup_proc.pid
        finally:
            sup_proc.terminate()
            sup_proc.wait()

    asyncio.run(_run())


def test_cross_process_agent_turn_rejected(temp_ipc_store):
    async def _run():
        store = temp_ipc_store
        sup_proc = subprocess.Popen([
            sys.executable,
            str(Path(__file__).parent.parent / "supervisor_process.py"),
            "--db-path",
            str(store.db_path),
            "--auto-reject",
            "--delay",
            "0.3",
            "--notes",
            "Rejected via pytest: budget reallocation policy violated.",
        ])

        try:
            runner = InMemoryRunner(cloud_operations_agent)
            user_id = "test_user_p2"
            session_id = str(uuid.uuid4())
            await runner.session_service.create_session(
                app_name=runner.app_name, user_id=user_id, session_id=session_id
            )

            res = await run_agent_turn(
                runner=runner,
                user_id=user_id,
                session_id=session_id,
                user_prompt="Transfer $300,000 from Engineering to Marketing to sponsor Q4 marketing events.",
                ipc_store=store,
                timeout_seconds=30.0,
            )
            assert res["status"] == "success"
            assert res["pending_tool"] == "transfer_budget_funds"
            assert res["auth_request"]["status"] == "REJECTED"
            assert res["auth_request"]["supervisor_pid"] == sup_proc.pid
        finally:
            sup_proc.terminate()
            sup_proc.wait()

    asyncio.run(_run())

