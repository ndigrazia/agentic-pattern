"""Agent definition and enterprise tools for Cross-Process Human-in-the-Loop.

Demonstrates Google ADK integration with critical tools gated by human authorization.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional
import uuid

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools import FunctionTool, ToolContext

load_dotenv()
logger = logging.getLogger("HITL.Agent")

MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")


# ============================================================================
# Routine Tools (Autonomous, No Confirmation Needed)
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
        "cpu_utilization": "92%",
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


# ============================================================================
# Critical Tools (Gated by Human Authorization Gate in External Process)
# ============================================================================

def reboot_production_cluster(
    cluster_id: str,
    reason: str,
    drain_nodes: bool = True,
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """Executes a rolling reboot on a production cloud Kubernetes cluster."""
    op_id = f"OP-REBOOT-{uuid.uuid4().hex[:6].upper()}"
    logger.info("Executing authorized cluster reboot %s for '%s'", op_id, cluster_id)
    return {
        "status": "reboot_initiated",
        "operation_id": op_id,
        "cluster_id": cluster_id,
        "drain_nodes": drain_nodes,
        "reason": reason,
        "message": (
            f"Production cluster reboot {op_id} successfully dispatched. "
            f"Drain nodes: {drain_nodes}. Cluster '{cluster_id}' is recovering."
        ),
    }


def transfer_budget_funds(
    from_dept: str,
    to_dept: str,
    amount_usd: float,
    justification: str = "Standard departmental budget reallocation",
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """Executes an irreversible financial budget reallocation between corporate departments."""
    tx_id = f"TX-ALLOC-{uuid.uuid4().hex[:6].upper()}"
    logger.info("Executing authorized budget transfer %s: $%.2f from %s to %s", tx_id, amount_usd, from_dept, to_dept)
    return {
        "status": "transfer_completed",
        "transaction_id": tx_id,
        "from_department": from_dept,
        "to_department": to_dept,
        "amount_usd": amount_usd,
        "justification": justification,
        "message": (
            f"Financial transfer {tx_id} executed. Successfully reallocated "
            f"${amount_usd:,.2f} from '{from_dept}' to '{to_dept}'."
        ),
    }


# Tools requiring supervisor confirmation before execution
reboot_cluster_tool = FunctionTool(reboot_production_cluster, require_confirmation=True)
transfer_budget_tool = FunctionTool(transfer_budget_funds, require_confirmation=True)


cloud_operations_agent = Agent(
    name="cloud_operations_assistant",
    model=MODEL_NAME,
    instruction="""
    You are an enterprise Cloud Infrastructure & Financial Operations Assistant.
    
    Workflow Guidelines:
    1. Read-only Telemetry & Balances:
       - Use 'get_cluster_status' when asked about cluster health, telemetry, or node diagnostics.
       - Use 'get_budget_status' when asked about department budgets or allocations.
    
    2. Critical Operations:
       - When requested to restart, reboot, or drain a production cloud cluster, immediately call 'reboot_production_cluster'.
       - When requested to reallocate, transfer, or move funds between departments, immediately call 'transfer_budget_funds'.
       - Note: These critical tools are protected by confirmation gates in our system. Always call the tool directly so the authorization gate can be triggered.
       - If the human supervisor approves the action, inform the user of the successful execution and operation/transaction ID.
       - If the human supervisor rejects the action, empathetically explain that the supervisor declined the request, cite the supervisor's feedback/notes, and recommend safe alternative next steps (such as submitting an RFC or contacting the finance director).
    """,
    tools=[
        get_cluster_status,
        get_budget_status,
        reboot_cluster_tool,
        transfer_budget_tool,
    ],
)

