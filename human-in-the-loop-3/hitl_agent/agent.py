"""Agent definition and enterprise tools for Cross-Process Human-in-the-Loop in ADK Web.

Demonstrates Google ADK integration where critical agent actions gate on human
authorization from a supervisor operating in a separate OS process via IPC.
Compatible with both CLI runners and the native `adk web` UI.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional
import uuid

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools import ToolContext

from ipc_store import DEFAULT_DB_FILENAME, IPCAuthorizationStore

load_dotenv()

logger = logging.getLogger("HITL3.Agent")

MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")

_SHARED_STORE: Optional[IPCAuthorizationStore] = None


def get_ipc_store() -> IPCAuthorizationStore:
    """Returns the singleton IPC authorization store instance."""
    global _SHARED_STORE
    if _SHARED_STORE is None:
        db_path = Path(__file__).parent.parent / DEFAULT_DB_FILENAME
        _SHARED_STORE = IPCAuthorizationStore(db_path)
    return _SHARED_STORE


# ============================================================================
# Routine Tools (Autonomous, No Human Gate Needed)
# ============================================================================

def get_cluster_status(cluster_id: str) -> Dict[str, Any]:
    """Retrieves operational telemetry, health state, and node metrics for a cloud cluster."""
    logger.info("Executing routine cluster telemetry inspection for '%s'", cluster_id)
    return {
        "status": "success",
        "cluster_id": cluster_id,
        "state": "DEGRADED_HEALTH",
        "nodes_total": 32,
        "nodes_unhealthy": 4,
        "region": "us-central1",
        "cpu_utilization": "94%",
        "recommendation": (
            f"Cluster '{cluster_id}' has 4 unresponsive worker nodes causing CPU pressure. "
            "A rolling reboot of the cluster is advised."
        ),
    }


def get_budget_status(department: str) -> Dict[str, Any]:
    """Retrieves budget limits, spent funds, and remaining balance for a department."""
    logger.info("Checking budget metrics for department '%s'", department)
    dept_lower = department.lower()
    if "data" in dept_lower or "ai" in dept_lower:
        return {
            "department": department,
            "annual_budget_usd": 500000.0,
            "spent_usd": 485000.0,
            "remaining_usd": 15000.0,
            "warning": "Budget depleted to 97%. Reallocation required for new compute workloads.",
        }
    return {
        "department": department,
        "annual_budget_usd": 800000.0,
        "spent_usd": 320000.0,
        "remaining_usd": 480000.0,
        "status": "healthy",
    }

def _extract_session_user(tool_context: Optional[ToolContext]) -> tuple[str, str]:
    if not tool_context:
        return ("adk-session", "adk-user")
    session_id = "adk-session"
    try:
        if hasattr(tool_context, "session") and tool_context.session:
            session_id = getattr(tool_context.session, "id", None) or getattr(tool_context.session, "session_id", None) or "adk-session"
        elif hasattr(tool_context, "session_id"):
            session_id = getattr(tool_context, "session_id", "adk-session")
    except Exception:
        pass
    user_id = getattr(tool_context, "user_id", "adk-user") if tool_context else "adk-user"
    return (str(session_id), str(user_id))


# ============================================================================
# Critical Tools (Gated by Human Supervisor Authorization in Other Process)
# ============================================================================

async def reboot_production_cluster(
    cluster_id: str,
    reason: str,
    drain_nodes: bool = True,
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """Executes a rolling reboot on a production cloud Kubernetes cluster.

    CRITICAL OPERATION: This action requires authorization from a human supervisor
    operating in another external process.
    """
    my_pid = os.getpid()
    ipc = get_ipc_store()
    session_id, user_id = _extract_session_user(tool_context)

    auth_req = ipc.create_request(
        session_id=session_id,
        user_id=user_id,
        function_call_id=f"call_{uuid.uuid4().hex[:8]}",
        tool_name="reboot_production_cluster",
        tool_args={"cluster_id": cluster_id, "reason": reason, "drain_nodes": drain_nodes},
        agent_pid=my_pid,
    )

    print("\n" + "=" * 75)
    print(f"🛑 [CROSS-PROCESS HITL DISPATCH - Agent PID: {my_pid}]")
    print(f"   Request ID:        {auth_req.request_id}")
    print(f"   Protected Tool:    reboot_production_cluster")
    print(f"   Target Cluster:    {cluster_id}")
    print(f"   Drain Nodes:       {drain_nodes}")
    print(f"   Reason:            {reason}")
    print(f"   Status:            PENDING HUMAN SUPERVISOR AUTHORIZATION IN OTHER PROCESS")
    print(f"⏳ Agent is PAUSED. Awaiting supervisor authorization from external process...")
    print("=" * 75, flush=True)

    try:
        decision = await ipc.wait_for_decision(auth_req.request_id, timeout_seconds=90.0)
    except TimeoutError:
        logger.warning("Reboot request %s timed out waiting for supervisor", auth_req.request_id)
        return {
            "status": "timed_out",
            "decision": "TIMEOUT",
            "cluster_id": cluster_id,
            "message": "Authorization request timed out after 90 seconds. Operation cancelled for safety.",
        }

    print("\n" + "=" * 75)
    print(f"📩 [AUTHORIZATION DECISION RECEIVED FROM EXTERNAL PROCESS]")
    print(f"   Request ID:        {decision.request_id}")
    print(f"   Supervisor PID:    {decision.supervisor_pid}")
    print(f"   Decision:          {'✅ APPROVED' if decision.status == 'APPROVED' else '❌ REJECTED'}")
    if decision.supervisor_notes:
        print(f"   Supervisor Notes:  \"{decision.supervisor_notes}\"")
    print("=" * 75, flush=True)

    if decision.status == "APPROVED":
        op_id = f"OP-REBOOT-{uuid.uuid4().hex[:6].upper()}"
        return {
            "status": "reboot_initiated",
            "decision": "APPROVED",
            "operation_id": op_id,
            "cluster_id": cluster_id,
            "drain_nodes": drain_nodes,
            "supervisor_pid": decision.supervisor_pid,
            "supervisor_notes": decision.supervisor_notes,
            "message": (
                f"Cluster reboot authorized by Supervisor (PID {decision.supervisor_pid}). "
                f"Operation {op_id} dispatched for cluster '{cluster_id}' with drain={drain_nodes}. "
                f"Supervisor note: \"{decision.supervisor_notes}\""
            ),
        }
    else:
        return {
            "status": "rejected_by_supervisor",
            "decision": "REJECTED",
            "cluster_id": cluster_id,
            "supervisor_pid": decision.supervisor_pid,
            "supervisor_notes": decision.supervisor_notes,
            "message": (
                f"Cluster reboot REJECTED by Supervisor (PID {decision.supervisor_pid}). "
                f"Reason: \"{decision.supervisor_notes}\". "
                "Operation was cancelled and no changes were made to the cluster."
            ),
        }


async def transfer_budget_funds(
    from_dept: str,
    to_dept: str,
    amount_usd: float,
    justification: str = "Standard departmental budget reallocation",
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """Executes a financial budget reallocation between corporate departments.

    CRITICAL OPERATION: This action requires authorization from a human supervisor
    operating in another external process.
    """
    my_pid = os.getpid()
    ipc = get_ipc_store()
    session_id, user_id = _extract_session_user(tool_context)

    auth_req = ipc.create_request(
        session_id=session_id,
        user_id=user_id,
        function_call_id=f"call_{uuid.uuid4().hex[:8]}",
        tool_name="transfer_budget_funds",
        tool_args={
            "from_dept": from_dept,
            "to_dept": to_dept,
            "amount_usd": amount_usd,
            "justification": justification,
        },
        agent_pid=my_pid,
    )

    print("\n" + "=" * 75)
    print(f"🛑 [CROSS-PROCESS HITL DISPATCH - Agent PID: {my_pid}]")
    print(f"   Request ID:        {auth_req.request_id}")
    print(f"   Protected Tool:    transfer_budget_funds")
    print(f"   Amount:            ${amount_usd:,.2f}")
    print(f"   From -> To:        {from_dept} -> {to_dept}")
    print(f"   Justification:     {justification}")
    print(f"   Status:            PENDING HUMAN SUPERVISOR AUTHORIZATION IN OTHER PROCESS")
    print(f"⏳ Agent is PAUSED. Awaiting supervisor authorization from external process...")
    print("=" * 75, flush=True)

    try:
        decision = await ipc.wait_for_decision(auth_req.request_id, timeout_seconds=90.0)
    except TimeoutError:
        logger.warning("Transfer request %s timed out waiting for supervisor", auth_req.request_id)
        return {
            "status": "timed_out",
            "decision": "TIMEOUT",
            "amount_usd": amount_usd,
            "message": "Authorization request timed out after 90 seconds. Transaction aborted.",
        }

    print("\n" + "=" * 75)
    print(f"📩 [AUTHORIZATION DECISION RECEIVED FROM EXTERNAL PROCESS]")
    print(f"   Request ID:        {decision.request_id}")
    print(f"   Supervisor PID:    {decision.supervisor_pid}")
    print(f"   Decision:          {'✅ APPROVED' if decision.status == 'APPROVED' else '❌ REJECTED'}")
    if decision.supervisor_notes:
        print(f"   Supervisor Notes:  \"{decision.supervisor_notes}\"")
    print("=" * 75, flush=True)

    if decision.status == "APPROVED":
        tx_id = f"TX-ALLOC-{uuid.uuid4().hex[:6].upper()}"
        return {
            "status": "transfer_completed",
            "decision": "APPROVED",
            "transaction_id": tx_id,
            "from_department": from_dept,
            "to_department": to_dept,
            "amount_usd": amount_usd,
            "supervisor_pid": decision.supervisor_pid,
            "supervisor_notes": decision.supervisor_notes,
            "message": (
                f"Financial transfer {tx_id} of ${amount_usd:,.2f} from '{from_dept}' to '{to_dept}' "
                f"successfully authorized by Supervisor (PID {decision.supervisor_pid}). "
                f"Supervisor note: \"{decision.supervisor_notes}\""
            ),
        }
    else:
        return {
            "status": "rejected_by_supervisor",
            "decision": "REJECTED",
            "from_department": from_dept,
            "to_department": to_dept,
            "amount_usd": amount_usd,
            "supervisor_pid": decision.supervisor_pid,
            "supervisor_notes": decision.supervisor_notes,
            "message": (
                f"Financial transfer of ${amount_usd:,.2f} from '{from_dept}' to '{to_dept}' was "
                f"REJECTED by Supervisor (PID {decision.supervisor_pid}). Reason: \"{decision.supervisor_notes}\"."
            ),
        }


# ============================================================================
# Root Agent Definition (Compatible with ADK Web & InMemoryRunner)
# ============================================================================

root_agent = Agent(
    name="cloud_operations_assistant",
    model=MODEL_NAME,
    instruction="""
    You are an enterprise Cloud Infrastructure & Financial Operations Assistant.

    Workflow Guidelines:
    1. Read-only Telemetry & Balances:
       - Use 'get_cluster_status' when asked about cluster health, telemetry, or node diagnostics.
       - Use 'get_budget_status' when asked about department budgets or allocations.

    2. Critical Operations (Gated by External Human Supervisor):
       - When requested to restart, reboot, or drain a production cloud cluster, immediately call 'reboot_production_cluster'.
       - When requested to reallocate, transfer, or move funds between departments, immediately call 'transfer_budget_funds'.
       - Note: These critical tools are protected by a cross-process Human-in-the-Loop authorization gate.
         Calling the tool automatically notifies the human supervisor in an external operations console.
       - If the tool result indicates 'APPROVED':
         Warmly notify the user of the successful execution, stating the Operation/Transaction ID, the supervisor's sign-off PID, and supervisor review notes.
       - If the tool result indicates 'REJECTED':
         Clearly explain to the user that the human supervisor in the operations process declined the request, quote the supervisor's specific reason/feedback, and propose appropriate next steps (e.g. submitting an RFC or contacting department leadership).
       - If the tool times out:
         Inform the user that the request timed out awaiting supervisor approval and was cancelled for safety.
    """,
    tools=[
        get_cluster_status,
        get_budget_status,
        reboot_production_cluster,
        transfer_budget_funds,
    ],
)

cloud_operations_agent = root_agent

