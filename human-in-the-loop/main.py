"""Human-in-the-Loop Pattern Implementation using Google ADK.

This module demonstrates the Human-in-the-Loop (HITL) pattern for agentic workflows.
Critical or sensitive operations (e.g., high-tier escalations, refunds, device replacements)
are gated behind human approval gates. The agent pauses execution when requesting confirmation,
and resumes only after receiving human supervisor authorization.
"""

import asyncio
import logging
import os
import sys
import uuid
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool, ToolContext
from google.genai import types
import nest_asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("HumanInTheLoopPattern")

load_dotenv()

MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")


# ============================================================================
# Support Tools
# ============================================================================

def troubleshoot_issue(issue: str) -> Dict[str, Any]:
    """Analyzes a technical problem and generates troubleshooting diagnostics."""
    logger.info("Executing automated troubleshooting for: '%s'", issue)
    return {
        "status": "success",
        "issue": issue,
        "diagnostics": (
            f"Automated diagnostics completed for '{issue}'. "
            "Recommended steps: 1. Power cycle device. 2. Verify firmware is up to date. "
            "3. Reset network and Bluetooth cache if applicable."
        ),
    }


def create_ticket(issue_type: str, details: str, priority: str = "normal") -> Dict[str, Any]:
    """Logs a standard technical support ticket into the ticketing system."""
    ticket_id = f"TICK-{uuid.uuid4().hex[:6].upper()}"
    logger.info("Creating support ticket %s (Priority: %s)", ticket_id, priority)
    return {
        "status": "success",
        "ticket_id": ticket_id,
        "issue_type": issue_type,
        "priority": priority,
        "details": details,
        "message": f"Support ticket {ticket_id} created successfully.",
    }


def escalate_to_human(
    issue_type: str,
    reason: str,
    urgency: str = "high",
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """Escalates complex, dangerous, or unresolved issues to a human specialist.

    This is a critical action gated by a Human-in-the-Loop confirmation gate.
    """
    escalation_id = f"ESC-{uuid.uuid4().hex[:6].upper()}"
    logger.info("Escalating to human specialist. Escalation ID: %s, Reason: %s", escalation_id, reason)
    return {
        "status": "escalated_to_human_specialist",
        "escalation_id": escalation_id,
        "assigned_queue": "Tier-3 Senior Technical Engineering",
        "issue_type": issue_type,
        "reason": reason,
        "urgency": urgency,
        "message": (
            f"Escalation {escalation_id} authorized. Session transferred to Tier-3 "
            "human engineering specialist for priority handling."
        ),
    }


def process_replacement_order(
    item_name: str,
    shipping_address: str,
    reason: str,
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """Issues a high-value hardware replacement order.

    Requires supervisor approval before dispatch.
    """
    rma_id = f"RMA-{uuid.uuid4().hex[:6].upper()}"
    logger.info("Processing replacement order %s for '%s'", rma_id, item_name)
    return {
        "status": "replacement_approved_and_dispatched",
        "rma_id": rma_id,
        "item": item_name,
        "shipping_address": shipping_address,
        "reason": reason,
        "message": f"Hardware replacement {rma_id} authorized and dispatched.",
    }


# ============================================================================
# Human-in-the-Loop Confirmation Gate Wrapping
# ============================================================================

# Tools requiring human confirmation before execution
escalate_to_human_tool = FunctionTool(escalate_to_human, require_confirmation=True)
process_replacement_tool = FunctionTool(process_replacement_order, require_confirmation=True)


# ============================================================================
# Personalization Callback
# ============================================================================

def personalization_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmRequest]:
    """Enriches the model prompt with customer profile and support history from state."""
    customer_info = callback_context.state.get("customer_info", {})
    if not customer_info:
        return None

    customer_name = customer_info.get("name", "Valued Customer")
    customer_tier = customer_info.get("tier", "Standard")
    recent_purchases = customer_info.get("recent_purchases", [])
    support_history = customer_info.get("support_history", [])

    personalization_lines = [
        "\n--- CUSTOMER CONTEXT (STATE) ---",
        f"Customer Name: {customer_name}",
        f"Account Tier: {customer_tier}",
    ]
    if recent_purchases:
        personalization_lines.append(f"Recent Purchases: {', '.join(recent_purchases)}")
    if support_history:
        personalization_lines.append(f"Support History: {'; '.join(support_history)}")
    personalization_lines.append(
        "Always personalize responses using this context, acknowledging their tier and purchase history."
    )
    personalization_lines.append("---------------------------------\n")

    personalization_note = "\n".join(personalization_lines)

    # Safely append to system instruction without using invalid role='system' in contents
    if llm_request.config:
        if isinstance(llm_request.config.system_instruction, str):
            llm_request.config.system_instruction += "\n" + personalization_note
        elif isinstance(llm_request.config.system_instruction, types.Content):
            llm_request.config.system_instruction.parts.append(
                types.Part.from_text(text=personalization_note)
            )
        elif llm_request.config.system_instruction is None:
            llm_request.config.system_instruction = personalization_note

    return None


# ============================================================================
# Technical Support Specialist Agent
# ============================================================================

technical_support_agent = Agent(
    name="technical_support_specialist",
    model=MODEL_NAME,
    instruction="""
    You are an empathetic, highly skilled technical support specialist for an electronics company.
    
    Workflow Guidelines:
    1. Check customer profile context: address the customer warmly by name and reference their tier/history.
    2. Routine Troubleshooting:
       - Use 'troubleshoot_issue' to diagnose common device problems.
       - Provide clear, step-by-step guidance.
       - If basic troubleshooting does not resolve the issue, use 'create_ticket'.
    3. Human-in-the-Loop Protected Actions:
       - For severe safety risks (e.g. smoking battery, fire hazard, physical device rupture) or
         when the customer explicitly requests human management, call 'escalate_to_human'.
       - For defective hardware requiring full unit replacement, call 'process_replacement_order'.
       - NOTE: These critical tools require human supervisor confirmation before they execute.
         If human approval is granted, inform the user of the confirmation details.
         If rejected, empathetically explain the situation and offer alternative support solutions.
    """,
    tools=[
        troubleshoot_issue,
        create_ticket,
        escalate_to_human_tool,
        process_replacement_tool,
    ],
    before_model_callback=personalization_callback,
)

# ============================================================================
# Human-in-the-Loop Interaction Runner
# ============================================================================

async def run_hitl_turn(
    runner: InMemoryRunner,
    user_id: str,
    session_id: str,
    user_prompt: str,
    auto_approve: Optional[bool] = True,
    interactive: bool = False,
) -> None:
    """Executes a conversation turn and handles human approval gates when triggered.

    Args:
        runner: InMemoryRunner instance.
        user_id: The ID of the user.
        session_id: The session ID.
        user_prompt: The user's input query.
        auto_approve: Whether to automatically approve (True) or reject (False)
                      the confirmation in automated demo mode.
        interactive: If True, asks for human input via CLI stdin.
    """
    print(f"\n💬 [Customer]: \"{user_prompt}\"")
    print("-" * 70)

    user_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_prompt)],
    )

    pending_confirmation_id: Optional[str] = None
    pending_tool_name: Optional[str] = None
    pending_args: Dict[str, Any] = {}

    # Stream agent events
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=user_message,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.function_call:
                    fc = part.function_call
                    if fc.name == "adk_request_confirmation":
                        pending_confirmation_id = fc.id
                        orig_fc = fc.args.get("originalFunctionCall", {})
                        pending_tool_name = orig_fc.get("name", "unknown")
                        pending_args = orig_fc.get("args", {})
                        print(f"\n🛑 [HITL Gate Triggered]: Approval required for tool '{pending_tool_name}'")
                        print(f"   Proposed Parameters: {pending_args}")
                    else:
                        print(f"⚙️  [Agent Call -> Tool '{fc.name}'] Args: {dict(fc.args or {})}")
                elif part.function_response:
                    fr = part.function_response
                    print(f"📥 [Tool Output <- '{fr.name}']: {fr.response}")
                elif part.text:
                    print(f"🤖 [Agent]:\n{part.text.strip()}")

    # If an approval gate was triggered, handle the human decision
    if pending_confirmation_id:
        print("\n" + "=" * 70)
        print("👤 [HUMAN SUPERVISOR REVIEW]")
        print(f"   Action pending:  '{pending_tool_name}'")
        print(f"   Details:         {pending_args}")
        print("=" * 70)

        decision: bool = True
        if interactive:
            user_input = input("👉 Human decision - Approve this action? [y/N]: ").strip().lower()
            decision = user_input in ("y", "yes")
        else:
            decision = bool(auto_approve)
            print(f"👉 Automated Supervisor Decision: {'✅ APPROVED' if decision else '❌ REJECTED'}")

        # Send confirmation response back to agent
        confirmation_msg = types.Content(
            role="user",
            parts=[
                types.Part(
                    function_response=types.FunctionResponse(
                        name="adk_request_confirmation",
                        id=pending_confirmation_id,
                        response={"confirmed": decision},
                    )
                )
            ],
        )

        print("\n🔄 Resuming agent execution with human decision...")
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=confirmation_msg,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.function_response:
                        fr = part.function_response
                        print(f"📥 [Post-Approval Tool Response <- '{fr.name}']: {fr.response}")
                    elif part.text:
                        print(f"\n🤖 [Agent Final Response]:\n{part.text.strip()}")

# ============================================================================
# Main Demonstration Scenarios
# ============================================================================

# ============================================================================
# Main Demonstration Scenarios
# ============================================================================

async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Google ADK Human-in-the-Loop Pattern Demo")
    parser.add_argument(
        "--scenario",
        choices=["1", "2", "3", "all"],
        default="2",
        help="Scenario to run: 1 (Autonomous), 2 (Escalation Approved), 3 (Replacement Rejected), or 'all' (default: 2)",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt human operator via CLI for live approval/rejection decisions",
    )
    args = parser.parse_args()

    nest_asyncio.apply()
    runner = InMemoryRunner(technical_support_agent)
    user_id = "user_sarah_connor"
    session_id = str(uuid.uuid4())

    # Initialize session and customer state
    session = await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )
    session.state["customer_info"] = {
        "name": "Sarah Connor",
        "tier": "Enterprise Platinum",
        "recent_purchases": ["CyberLaptop Ultra 16", "Wireless Studio ANC Headset"],
        "support_history": ["Power adapter replaced under warranty in September"],
    }

    print("=" * 75)
    print("🚀 GOOGLE ADK HUMAN-IN-THE-LOOP (HITL) PATTERN")
    print(f"   Model: {MODEL_NAME}")
    print(f"   Customer: {session.state['customer_info']['name']} ({session.state['customer_info']['tier']})")
    print(f"   Selected Scenario: {args.scenario} | Interactive Mode: {args.interactive}")
    print("=" * 75)

    # ------------------------------------------------------------------------
    # Scenario 1: Autonomous Handling (No Human Gate Required)
    # ------------------------------------------------------------------------
    if args.scenario in ("1", "all"):
        print("\n" + "#" * 75)
        print("### SCENARIO 1: Autonomous Diagnostics & Troubleshooting")
        print("### Expected: Agent troubleshoots routine issue without human gate.")
        print("#" * 75)
        await run_hitl_turn(
            runner=runner,
            user_id=user_id,
            session_id=session_id,
            user_prompt="My Wireless Studio ANC Headset keeps dropping Bluetooth connection to my laptop.",
            interactive=args.interactive,
        )

    # ------------------------------------------------------------------------
    # Scenario 2: Critical Escalation - Human Approves (HITL Gate -> APPROVED)
    # ------------------------------------------------------------------------
    if args.scenario in ("2", "all"):
        print("\n\n" + "#" * 75)
        print("### SCENARIO 2: Safety Hazard - Human Escalation (APPROVED)")
        print("### Expected: Agent requests escalation -> Supervisor APPROVES -> Escalated.")
        print("#" * 75)
        await run_hitl_turn(
            runner=runner,
            user_id=user_id,
            session_id=session_id,
            user_prompt=(
                "Emergency! My CyberLaptop Ultra 16 battery is swelling, extremely hot, and smells like smoke! "
                "I need an immediate escalation to a human specialist!"
            ),
            auto_approve=True,
            interactive=args.interactive,
        )

    # ------------------------------------------------------------------------
    # Scenario 3: High-Value Replacement - Human Rejects (HITL Gate -> REJECTED)
    # ------------------------------------------------------------------------
    if args.scenario in ("3", "all"):
        print("\n\n" + "#" * 75)
        print("### SCENARIO 3: High-Value Hardware Replacement - Human Rejects (REJECTED)")
        print("### Expected: Agent proposes replacement -> Supervisor REJECTS -> Fallback ticket.")
        print("#" * 75)
        await run_hitl_turn(
            runner=runner,
            user_id=user_id,
            session_id=session_id,
            user_prompt=(
                "My CyberLaptop Ultra 16 internal cooling fan failed completely and the motherboard is fried. "
                "Please dispatch a replacement unit to 742 Evergreen Terrace."
            ),
            auto_approve=False,
            interactive=args.interactive,
        )

    print("\n" + "=" * 75)
    print("✅ Human-in-the-Loop Pattern Demonstrations Completed Successfully.")
    print("=" * 75)
    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(main())

