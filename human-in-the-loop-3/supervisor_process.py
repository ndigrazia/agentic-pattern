"""Human Supervisor Process for Cross-Process Human-in-the-Loop in Google ADK.

Provides an independent process interface for a human operator or automated supervisor
to review, authorize, or reject critical agent actions dispatched from ADK Web or CLI.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import sys
import time
from typing import Optional

from ipc_store import AuthorizationRequest, DEFAULT_DB_FILENAME, IPCAuthorizationStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("HITL3.SupervisorProcess")


def display_request_card(req: AuthorizationRequest, supervisor_pid: int) -> None:
    print("\n" + "=" * 70)
    print(f"🚨 [HUMAN SUPERVISOR REVIEW DASHBOARD - Supervisor PID: {supervisor_pid}]")
    print("=" * 70)
    print(f"  Request ID:       {req.request_id}")
    print(f"  Agent PID:        {req.agent_pid}")
    print(f"  Session ID:       {req.session_id}")
    print(f"  Protected Action: {req.tool_name}")
    print(f"  Arguments:        {json.dumps(req.tool_args, indent=2)}")
    print(f"  Status:           {req.status}")
    print(f"  Created At:       {req.created_at}")
    print("=" * 70)


def run_interactive_loop(ipc_store: IPCAuthorizationStore, poll_interval: float = 1.0) -> None:
    my_pid = os.getpid()
    print("=" * 70)
    print(f"👤 Human Supervisor Process Started (PID: {my_pid})")
    print(f"   Connected to IPC Store: {ipc_store.db_path}")
    print("   Waiting for authorization requests from Agent (ADK Web or CLI)...")
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
                    ipc_store.resolve_request(
                        req.request_id,
                        approved=True,
                        notes=notes or "Approved by supervisor in external console",
                        supervisor_pid=my_pid,
                    )
                    print(f"✅ Approved request {req.request_id}. Agent unblocked!\n")
                elif choice in ("n", "no"):
                    notes = input("👉 Rejection reason: ").strip()
                    ipc_store.resolve_request(
                        req.request_id,
                        approved=False,
                        notes=notes or "Rejected by supervisor policy",
                        supervisor_pid=my_pid,
                    )
                    print(f"❌ Rejected request {req.request_id}. Agent notified!\n")
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
    session_id: Optional[str] = None,
) -> int:
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
                if session_id and req.session_id != session_id:
                    continue
                print(
                    f"\n🚨 [Supervisor PID: {my_pid}]: Received request {req.request_id} "
                    f"for tool '{req.tool_name}' from Agent PID {req.agent_pid}"
                )
                print(f"⏳ Simulating human review time ({delay_seconds:.1f}s)...")
                time.sleep(delay_seconds)

                try:
                    ipc_store.resolve_request(
                        request_id=req.request_id,
                        approved=auto_approve,
                        notes=final_notes,
                        supervisor_pid=my_pid,
                    )
                except ValueError as e:
                    logger.debug("Request %s already resolved: %s", req.request_id, e)
                    continue
                decided_count += 1
                icon = "✅" if auto_approve else "❌"
                print(
                    f"{icon} [Supervisor PID: {my_pid}]: Request {req.request_id} "
                    f"-> {decision_str}D with notes: \"{final_notes}\""
                )

                if max_decisions is not None and decided_count >= max_decisions:
                    print(f"Reached max decisions limit ({max_decisions}). Exiting supervisor daemon.")
                    return decided_count

            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("\nAutomated supervisor stopped.")
        return decided_count


def list_requests(ipc_store: IPCAuthorizationStore) -> None:
    requests = ipc_store.get_all_requests(limit=20)
    if not requests:
        print("No authorization requests recorded yet in IPC store.")
        return

    print("\n" + "=" * 90)
    print(f"📋 IPC AUTHORIZATION REQUEST AUDIT LOG ({ipc_store.db_path})")
    print("=" * 90)
    for r in requests:
        icon = {"PENDING": "⏳", "APPROVED": "✅", "REJECTED": "❌", "EXPIRED": "⏰"}.get(r.status, "❓")
        print(
            f"{icon} [{r.status:8}] {r.request_id} | Tool: {r.tool_name:<26} | Agent PID: {r.agent_pid:<6} | "
            f"Sup PID: {str(r.supervisor_pid or '-'):<6} | Created: {r.created_at[:19]}"
        )
        if r.supervisor_notes:
            print(f"    Notes: {r.supervisor_notes}")
    print("=" * 90 + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Human Supervisor Process for Google ADK Cross-Process HITL")
    parser.add_argument("--db-path", type=str, default=None, help="Path to SQLite IPC store DB file")
    parser.add_argument("--auto-approve", action="store_true", help="Run in automated supervisor mode approving requests")
    parser.add_argument("--auto-reject", action="store_true", help="Run in automated supervisor mode rejecting requests")
    parser.add_argument("--delay", type=float, default=1.0, help="Simulated human review delay in seconds (auto mode)")
    parser.add_argument("--max-decisions", type=int, default=None, help="Maximum number of decisions before exiting")
    parser.add_argument("--notes", type=str, default=None, help="Custom notes to record with decision")
    parser.add_argument("--session-id", type=str, default=None, help="Filter to only resolve requests from specific session")
    parser.add_argument("--list", action="store_true", help="List recent authorization requests and exit")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    store = IPCAuthorizationStore(args.db_path)

    if args.list:
        list_requests(store)
        return

    if args.auto_approve or args.auto_reject:
        run_automated_supervisor(
            ipc_store=store,
            auto_approve=args.auto_approve,
            delay_seconds=args.delay,
            max_decisions=args.max_decisions,
            notes=args.notes,
            session_id=args.session_id,
        )
    else:
        run_interactive_loop(ipc_store=store)


if __name__ == "__main__":
    main()
