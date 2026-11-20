# Cross-Process Human-in-the-Loop (HITL) Pattern

This directory demonstrates an enterprise-grade **Human-in-the-Loop (HITL)** architecture using the **Google Agent Development Kit (ADK)** where critical agent actions are gated behind authorization from a human supervisor operating in a **separate OS process**.

---

## 🎯 Architectural Motivation

In enterprise deployments, autonomous AI agents should rarely prompt the user or console operator directly within their own execution thread. Instead, security, operational safety, and compliance require:

1. **Separation of Concerns**: Agent workloads run as headless backend services or worker processes (PID A).
2. **Dedicated Supervisor Interfaces**: Human approvers (supervisors, site reliability engineers, financial controllers) review pending actions in dedicated operational consoles, ticketing dashboards, or CLI tools in another process (PID B).
3. **Decoupled Asynchronous Lifecycle**: The agent halts execution at the tool confirmation gate, publishes an authorization request to a shared Inter-Process Communication (IPC) channel, and sleeps until the supervisor in the other process approves or rejects the action.
4. **Google ADK Native Integration**: Seamlessly resumes Google ADK's native `adk_request_confirmation` tool confirmation flow once the cross-process decision arrives.

---

## 🏗️ Architecture & Cross-Process Sequence

```
  AGENT PROCESS (PID: A)                               HUMAN SUPERVISOR (PID: B)
  +-------------------------+                          +-------------------------+
  |  Google ADK Agent       |                          |  Terminal 2 Dashboard   |
  |  Calls Protected Tool   |                          +-------------------------+
  +------------+------------+                                       ^
               | 1. adk_request_confirmation                        |
               v                                                    |
  +-------------------------------------------------------------+   | 3. Displays
  |                   SQLite WAL IPC STORE                      |   |    pending
  |                 (hitl_auth_requests.db)                     |---+    requests
  |  - request_id: AUTH-XXXX                                    |
  |  - tool_name: reboot_production_cluster                     |<--+ 4. Human approves
  |  - tool_args: {'cluster_id': 'prod-01'}                     |        or rejects
  |  - agent_pid: A | supervisor_pid: B                         |
  |  - status: PENDING -> APPROVED / REJECTED                   |
  +-------------------------------------------------------------+
               |
               | 5. Decision polled & returned
               v
  +-------------------------+
  |  Agent Resumes ADK      |
  |  Executes or Fallbacks  |
  +-------------------------+
```


---

## 📦 Components

| Component | File | Description |
|-----------|------|-------------|
| **IPC Store** | `ipc_store.py` | SQLite WAL-backed inter-process store supporting concurrent reads and writes from different OS processes. |
| **Agent & Tools** | `agent.py` | Google ADK Agent (`cloud_operations_assistant`) with routine tools (`get_cluster_status`, `get_budget_status`) and gated tools (`reboot_production_cluster`, `transfer_budget_funds`). |
| **Agent Process** | `agent_process.py` | Runs ADK streaming execution, detects confirmation gates, delegates authorization to the IPC store, pauses execution, and resumes once decided. |
| **Supervisor Process** | `supervisor_process.py` | Dedicated operator CLI interface running in another process/terminal for interactive approval/rejection or automated supervisor review. |
| **Main Orchestrator** | `main.py` | Top-level driver supporting multi-process automated demonstrations or single-role execution. |
| **Unit & Integration Tests** | `tests/test_hitl_multiprocess.py` | Complete test suite verifying cross-process approval, rejection, timeouts, and SQLite ACID guarantees. |

---

## 🚀 How to Run

### Mode 1: Automated Multi-Process Demonstration

Run the automated orchestrator which spawns the human supervisor daemon in a separate background OS process:

```bash
# Scenario 1: Autonomous Diagnostics (No human confirmation gate needed)
uv run python main.py --scenario 1

# Scenario 2: Critical Cluster Reboot (Human supervisor in other process APPROVES)
uv run python main.py --scenario 2

# Scenario 3: High-Value Budget Transfer (Human supervisor in other process REJECTS)
uv run python main.py --scenario 3

# Run all scenarios sequentially
uv run python main.py --scenario all
```

---

### Mode 2: Real-World Dual-Terminal Interactive Operation

To simulate a real production workflow with a human operator reviewing actions live in a separate console:

#### Terminal 1 (Agent Service)
```bash
uv run python main.py --role agent --scenario 2
```
*The agent begins processing the user's request. Upon hitting the `reboot_production_cluster` tool, the agent emits an authorization request to the IPC store and pauses execution.*

#### Terminal 2 (Human Supervisor Console)
```bash
uv run python supervisor_process.py
```
*The supervisor dashboard detects the pending request from Terminal 1, displaying the agent PID, target cluster, and reason.*
*The human enters `y` to approve (with optional supervisor notes) or `n` to reject.*

*Immediately upon confirmation in Terminal 2, Terminal 1 unblocks, resumes the Google ADK runner, executes the authorized tool, and reports the final result to the user!*

---

### Mode 3: Supervisor CLI Commands

The supervisor process also provides standalone commands for operational inspection:

```bash
# List all pending requests
uv run python supervisor_process.py --list

# Run auto-pilot supervisor with custom review delay
uv run python supervisor_process.py --auto-approve --delay 2.0
uv run python supervisor_process.py --auto-reject --delay 1.0 --notes "Budget threshold exceeded"
```

---

## 🧪 Running Tests

Run the full pytest suite:

```bash
uv run pytest tests/test_hitl_multiprocess.py -v
```

