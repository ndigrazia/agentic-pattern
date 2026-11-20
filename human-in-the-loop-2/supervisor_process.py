"""Human Supervisor Process for Cross-Process Human-in-the-Loop.

Provides an independent process interface for a human operator or automated supervisor
to review, authorize, or reject critical agent actions via the IPC store.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from typing import Optional

from ipc_store import AuthorizationRequest, IPCAuthorizationStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("HITL.SupervisorProcess")


def display_request_card(req: AuthorizationRequest, supervisor_pid: int) -> None:
    """Formats and prints an authorization request for human review."""
    print("\n" + "=" * 70)
    print(f"🚨 [HUMAN SUPERVISOR REVIEW DASHBOARD - Supervisor PID: {supervisor_pid}]")
    print("=" * 70)
    print(f"  Request ID:       {req.request_id}")
    print(f"  Agent PID:        {req.agent_pid}")
    print(f"  Session ID:       {req.session_id}")
    print(f"  Protected Action: {req.tool_name}")
    print(f"  Arguments:        {json.dumps(req.tool_args, indent=2)}")
    print(f"  Created At:       {req.created_at}")
    print("=" * 70)


def run_interactive_loop(ipc_store: IPCAuthorizationStore, poll_interval: float = 1.0) -> None:
    """Runs continuous interactive CLI listening for incoming agent authorization requests."""
    my_pid = os.getpid()
    print("=" * 70)
    print(f"👤 Human Supervisor Process Started (PID: {my_pid})")
    print(f"   Connected to IPC Store: {ipc_store.db_path}")
    print("   Waiting for authorization requests from the Agent Process...")
    print("=" * 70)

    last_logged_empty = False
    try:
        while True:
            pending = ipc_store.get_pending_requests()
            if not pending:
                if not last_logged_empty:
                    print(f"⏳ [Supervisor PID {my_pid}]: No pending requests. Listening... (Ctrl+C to quit)")
                    last_logged_empty = True
                time.sleep(poll_interval)
                continue

            last_logged_empty = False
            for req in pending:
                display_request_card(req, my_pid)
                choice = input("👉 Authorize action? [y=Approve / n=Reject / s=Skip / q=Quit]: ").strip().lower()
                if choice in ("y", "yes"):
                    notes = input("👉 Optional approval note: ").strip()
                    ipc_store.resolve_request(req.request_id, approved=True, notes=notes or "Approved by supervisor", supervisor_pid=my_pid)
                    print(f"✅ Approved request {req.request_id}. Agent process resumed!\n")
                elif choice in ("n", "no"):
                    notes = input("👉 Rejection reason: ").strip()
                    ipc_store.resolve_request(req.request_id, approved=False, notes=notes or "Rejected by supervisor policy", supervisor_pid=my_pid)
                    print(f"❌ Rejected request {req.request_id}. Agent process notified!\n")
                elif choice == "q":
                    print("Exiting supervisor process.")
                    return
                elif choice == "s":
                    print("Skipping request for now.\n")
                    continue
                else:
                    print("Invalid choice. Skipping.")

            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("\nSupervisor process stopped by operator.")


def run_automated_supervisor(
    ipc_store: IPCAuthorizationStore,
    auto_approve: bool = True,
    delay_seconds: float = 1.0,
    max_decisions: Optional[int] = None,
    poll_interval: float = 0.5,
    notes: Optional[str] = None,
) -> int:
    """Runs an automated supervisor daemon that resolves incoming requests after a delay."""
    my_pid = os.getpid()
    decided_count = 0
    decision_str = "APPROVE" if auto_approve else "REJECT"
    default_notes = (
        "Automated supervisor approval: verified within operational thresholds."
        if auto_approve
        else "Automated supervisor rejection: policy check failed (financial threshold/safety limit)."
    )
    final_notes = notes or default_notes

    print(
        f"🤖 [Automated Supervisor Process (PID: {my_pid})]: "
        f"Configured to {decision_str} requests after {delay_seconds:.1f}s review delay."
    )

    try:
        while True:
            pending = ipc_store.get_pending_requests()
            for req in pending:
                print(
                    f"\n🚨 [Supervisor PID: {my_pid}]: Received request {req.request_id} "
                    f"for tool '{req.tool_name}' from Agent PID {req.agent_pid}"
                )
                print(f"⏳ Simulating human review time ({delay_seconds:.1f}s)...")
                time.sleep(delay_seconds)

                ipc_store.resolve_request(
                    request_id=req.request_id,
                    approved=auto_approve,
                    notes=final_notes,
                    supervisor_pid=my_pid,
                )
                print(
                    f"👉 [Supervisor PID: {my_pid}]: {decision_str}D request {req.request_id}. "
                    f"Agent process PID {req.agent_pid} unblocked!"
                )
                decided_count += 1
                if max_decisions and decided_count >= max_decisions:
                    return decided_count

            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print(f"\nAutomated supervisor stopped. Total decided: {decided_count}")
    return decided_count


def main():
    parser = argparse.ArgumentParser(description="Human Supervisor Process for Cross-Process HITL")
    parser.add_argument("--db-path", default=None, help="Path to SQLite IPC database")
    parser.add_argument("--interactive", action="store_true", help="Run interactive terminal review CLI")
    parser.add_argument("--auto-approve", action="store_true", help="Auto-approve incoming requests")
    parser.add_argument("--auto-reject", action="store_true", help="Auto-reject incoming requests")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay before auto-deciding (seconds)")
    parser.add_argument("--notes", default=None, help="Custom notes for decisions")
    parser.add_argument("--list", action="store_true", help="List all pending authorization requests and exit")

    args = parser.parse_args()
    ipc_store = IPCAuthorizationStore(args.db_path)

    if args.list:
        pending = ipc_store.get_pending_requests()
        print(f"Pending Authorization Requests ({len(pending)}):")
        for r in pending:
            print(f"- {r.request_id} | Agent PID: {r.agent_pid} | Tool: {r.tool_name} | Args: {r.tool_args}")
        return

    if args.auto_approve:
        run_automated_supervisor(ipc_store, auto_approve=True, delay_seconds=args.delay, notes=args.notes)
    elif args.auto_reject:
        run_automated_supervisor(ipc_store, auto_approve=False, delay_seconds=args.delay, notes=args.notes)
    else:
        run_interactive_loop(ipc_store)


if __name__ == "__main__":
    main()

