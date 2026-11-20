"""Agent Process for Cross-Process Human-in-the-Loop.

Executes Google ADK agent tasks and gates critical actions by requesting
authorization from a human supervisor operating in another process via IPC.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional
import uuid

from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from google.genai import types

from agent import cloud_operations_agent
from ipc_store import AuthorizationRequest, IPCAuthorizationStore

load_dotenv()
logger = logging.getLogger("HITL.AgentProcess")


async def run_agent_turn(
    runner: InMemoryRunner,
    user_id: str,
    session_id: str,
    user_prompt: str,
    ipc_store: IPCAuthorizationStore,
    timeout_seconds: float = 60.0,
    poll_interval: float = 0.5,
) -> Dict[str, Any]:
    """Executes a conversation turn and delegates confirmation gates to an external process."""
    my_pid = os.getpid()
    print(f"\n💬 [User Query]: \"{user_prompt}\"")
    print(f"🤖 [Agent Process (PID: {my_pid})]: Processing request with Google ADK...")

    initial_msg = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_prompt)],
    )

    pending_confirmation_id: Optional[str] = None
    pending_tool_name: Optional[str] = None
    pending_tool_args: Dict[str, Any] = {}
    auth_request: Optional[AuthorizationRequest] = None
    agent_responses: list[str] = []

    # Stream agent events
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
                if fc.name == "adk_request_confirmation":
                    pending_confirmation_id = fc.id
                    orig_fc = fc.args.get("originalFunctionCall", {}) if fc.args else {}
                    pending_tool_name = orig_fc.get("name", "unknown_tool")
                    pending_tool_args = orig_fc.get("args", {})
                    print(
                        f"\n🛑 [Agent Process (PID: {my_pid})]: "
                        f"CRITICAL GATE TRIGGERED for tool '{pending_tool_name}'!"
                    )
                else:
                    print(f"⚙️  [Agent Process]: Calling autonomous tool -> {fc.name}({fc.args})")

            elif part.function_response:
                fr = part.function_response
                print(f"📥 [Agent Process]: Autonomous Tool Response <- '{fr.name}': {fr.response}")

            elif part.text:
                text = part.text.strip()
                agent_responses.append(text)
                print(f"\n🤖 [Agent Response]:\n{text}")

    # If a critical gate was triggered, delegate authorization to external supervisor process
    if pending_confirmation_id and pending_tool_name:
        auth_request = ipc_store.create_request(
            session_id=session_id,
            user_id=user_id,
            function_call_id=pending_confirmation_id,
            tool_name=pending_tool_name,
            tool_args=pending_tool_args,
            agent_pid=my_pid,
        )

        print("\n" + "=" * 75)
        print(f"📡 [CROSS-PROCESS HITL DISPATCH - Agent PID: {my_pid}]")
        print(f"   Request ID:        {auth_request.request_id}")
        print(f"   Protected Tool:    {pending_tool_name}")
        print(f"   Tool Arguments:    {pending_tool_args}")
        print(f"   Status:            PENDING SUPERVISOR AUTHORIZATION IN OTHER PROCESS")
        print(f"⏳ Agent process is PAUSED. Awaiting human authorization from external process...")
        print("=" * 75)

        decision_approved = False
        notes = ""
        try:
            resolved_req = await ipc_store.wait_for_decision(
                request_id=auth_request.request_id,
                timeout_seconds=timeout_seconds,
                poll_interval=poll_interval,
            )
            decision_approved = (resolved_req.status == "APPROVED")
            notes = resolved_req.supervisor_notes
            auth_request = resolved_req

            print("\n" + "=" * 75)
            print(f"📩 [AUTHORIZATION RECEIVED FROM EXTERNAL PROCESS]")
            print(f"   Request ID:     {resolved_req.request_id}")
            print(f"   Supervisor PID: {resolved_req.supervisor_pid}")
            print(f"   Decision:       {'✅ APPROVED' if decision_approved else '❌ REJECTED'}")
            if notes:
                print(f"   Review Notes:   \"{notes}\"")
            print("=" * 75)

        except TimeoutError:
            print(f"\n⚠️  [Agent Process]: Timed out waiting for supervisor after {timeout_seconds}s!")
            decision_approved = False
            notes = "Authorization timed out. Automatically rejected for safety."

        confirmation_msg = types.Content(
            role="user",
            parts=[
                types.Part(
                    function_response=types.FunctionResponse(
                        name="adk_request_confirmation",
                        id=pending_confirmation_id,
                        response={"confirmed": decision_approved},
                    )
                )
            ],
        )

        print("\n🔄 [Agent Process]: Resuming Google ADK execution with supervisor decision...")
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=confirmation_msg,
        ):
            if not event.content or not event.content.parts:
                continue

            for part in event.content.parts:
                if part.function_response:
                    fr = part.function_response
                    print(f"📥 [Post-Approval Tool Result <- '{fr.name}']: {fr.response}")
                elif part.text:
                    text = part.text.strip()
                    agent_responses.append(text)
                    print(f"\n🤖 [Agent Final Answer]:\n{text}")

    return {
        "status": "success",
        "pending_tool": pending_tool_name,
        "auth_request": auth_request.to_dict() if auth_request else None,
        "responses": agent_responses,
    }

