# Cross-Process Human-in-the-Loop (HITL) with Google ADK Web

This directory demonstrates an enterprise-grade **Cross-Process Human-in-the-Loop (HITL)** architecture built on the **Google Agent Development Kit (ADK)** and verified on **`adk web`**. Critical agent operations are protected by gating execution on authorization from a human supervisor operating in an **independent OS process** via a shared SQLite WAL IPC channel.

---

## 🎯 Architecture & Motivation

In enterprise environments, AI agents serving web clients or background automations must not execute dangerous, high-impact operations (such as restarting production clusters or reallocating financial budgets) without human supervisor approval. Furthermore, the human supervisor should not be the casual web chat user, but rather an authorized operator (e.g. SRE on-call, financial controller) operating in a dedicated operations terminal or external console.

### Key Capabilities

1. **Native Google ADK Web Integration**: Served by Google ADK's FastAPI DevServer (`adk web`), exposing the `hitl_agent` application and standard endpoints (`/list-apps`, `/run`, `/run_sse`, Web UI).
2. **Cross-Process Separation of Concerns**:
   - **Agent Service (PID A)**: Runs inside `adk web` serving HTTP/SSE requests and web UI clients.
   - **Supervisor Console (PID B)**: Runs in a separate process or terminal (`supervisor_process.py`), displaying pending authorization cards and gathering human sign-off with audit notes.
3. **Decoupled Asynchronous IPC Store**: High-concurrency SQLite WAL-backed IPC store (`hitl_auth_requests.db`) supporting multi-process ACID transactions, atomic status transitions (`PENDING` -> `APPROVED` / `REJECTED`), and async waiting.
4. **Resilience & Safety**: Automated timeout gates (e.g. 90s) prevent indefinite hangs by safely rejecting expired requests if no supervisor responds.
5. **Full Audit Traceability**: Agent responses cite the authorizing supervisor's OS PID, timestamp, review notes, and generated operation/transaction IDs.

---

## 🏗️ Cross-Process Architecture Diagram

```
   ADK WEB SERVER (PID: A)                             HUMAN SUPERVISOR (PID: B)
   +------------------------------+                    +------------------------------+
   |  `adk web` (FastAPI Server)   |                    |  Terminal 2 Operations CLI   |
   |  - Web UI / HTTP Client      |                    |  `supervisor_process.py`     |
   |  - LlmAgent (Gemini 2.5)     |                    +------------------------------+
   +--------------+---------------+                                   ^
                  |                                                   |
                  | 1. User prompts critical action                   | 3. Displays pending
                  | 2. Protected tool creates request                 |    request card
                  v                                                   |
   +--------------------------------------------------------------+   |
   |                  SQLite WAL IPC STORE                        |---+
   |                (hitl_auth_requests.db)                       |
   |  - request_id: AUTH-XXXX                                     |<--+ 4. Human supervisor
   |  - tool_name: reboot_production_cluster                      |        enters 'y'/'n' + notes
   |  - tool_args: {'cluster_id': 'prod-uscentral-01'}            |
   |  - agent_pid: A | supervisor_pid: B                          |
   |  - status: PENDING -> APPROVED / REJECTED                    |
   +--------------------------------------------------------------+
                  |
                  | 5. Tool unblocks on decision
                  v
   +------------------------------+
   |  Tool executes or aborts     |
   |  Agent returns final audit   |
   |  result to user in ADK Web   |
   +------------------------------+
```

---

## 📦 Directory Structure

| File / Folder | Description |
|---|---|
| `hitl_agent/agent.py` | Google ADK Agent (`root_agent`) with routine tools (`get_cluster_status`, `get_budget_status`) and gated tools (`reboot_production_cluster`, `transfer_budget_funds`). |
| `hitl_agent/__init__.py` | Package entrypoint exposing `root_agent` for ADK discovery. |
| `ipc_store.py` | Concurrent SQLite WAL store for cross-process authorization requests and decisions. |
| `supervisor_process.py` | Dedicated operator CLI running in another OS process (interactive prompt or automated daemon). |
| `prove_adk_web.py` | Automated proof script launching live `adk web`, spawning supervisor process, and proving HITL end-to-end. |
| `main.py` | Top-level CLI driver supporting multi-process automated demonstrations or single-role execution. |
| `tests/test_hitl_adk_web.py` | Complete Pytest suite verifying IPC store, ADK Web app discovery, and cross-process HITL flows. |
| `pyproject.toml` | Workspace package dependencies (`google-adk`, `google-genai`, `httpx`, `pytest`). |
| `.env` | Environment configuration (`GEMINI_MODEL_NAME`, `GOOGLE_API_KEY`). |

---


## 🚀 How to Run & Prove in ADK Web

### 🌟 1. Automated Proof in Live ADK Web Server

Run the dedicated proof script which automatically boots `adk web` on a local port, spawns the human supervisor daemon in an independent OS process, sends user prompts via HTTP, and validates the entire cross-process flow:

```bash
uv run python prove_adk_web.py
```
*(Or alternatively: `uv run python main.py --prove-adk-web`)*

**Proof Output:**
- **Proof 1 (Reboot Approved)**:
  - Agent in `adk web` (PID: A) receives reboot request.
  - Pauses execution and dispatches `AUTH-XXXX` to SQLite IPC store.
  - Supervisor in Process B (PID: B) detects request, reviews, and logs `APPROVED`.
  - Agent unblocks, executes reboot `OP-REBOOT-XXXX`, and reports supervisor PID + notes in the Web response.
- **Proof 2 (Budget Transfer Rejected)**:
  - Agent in `adk web` (PID: A) receives high-value budget transfer ($250k).
  - Pauses execution and dispatches request to SQLite IPC store.
  - Supervisor in Process B (PID: B) rejects with notes: *"Reallocation exceeds $50k discretionary ceiling."*
  - Agent unblocks, catches rejection, and empathetically explains refusal and next steps in the Web response.

---

### 🌐 2. Interactive Browser + External Terminal Operation

Experience the exact real-world operator workflow with a browser on one screen and the supervisor terminal on another:

#### Step 1: Start ADK Web Server
In **Terminal 1**, start the ADK Web server:
```bash
uv run python -m google.adk.cli web . --port 8000
```
Open your browser at **`http://127.0.0.1:8000`** and select **`hitl_agent`** from the application list.

#### Step 2: Start Human Supervisor Console
In **Terminal 2**, start the independent human supervisor process:
```bash
uv run python supervisor_process.py
```

#### Step 3: Trigger Protected Action in Browser
In the **ADK Web UI chat**, type:
> *"Please execute a rolling reboot of production cluster prod-uscentral-01 due to unresponsive nodes."*

#### Step 4: Authorize in Terminal 2
Watch **Terminal 2** immediately light up with the request card:
```
🚨 [HUMAN SUPERVISOR REVIEW DASHBOARD - Supervisor PID: 12345]
  Request ID:       AUTH-9B3C84F1
  Agent PID:        12300 (ADK Web Server)
  Protected Action: reboot_production_cluster
  Arguments:        {"cluster_id": "prod-uscentral-01", "reason": "unresponsive nodes"}
👉 Authorize action? [y=Approve / n=Reject / s=Skip / q=Quit]: y
👉 Optional approval note: Approved rolling reboot after checking Grafana alerts.
```

As soon as you enter `y` in Terminal 2:
- The ADK Web chat unblocks and responds:
  *"The rolling reboot of production cluster prod-uscentral-01 has been successfully initiated. Operation ID: OP-REBOOT-..., approved by Supervisor (PID 12345)."*

---

### 🎬 3. Running Pre-Packaged Scenarios via CLI

You can also run automated multi-process scenarios directly:

```bash
# Scenario 1: Autonomous Diagnostics (No human confirmation gate needed)
uv run python main.py --scenario 1

# Scenario 2: Critical Cluster Reboot (External supervisor approves)
uv run python main.py --scenario 2

# Scenario 3: High-Value Budget Transfer (External supervisor rejects)
uv run python main.py --scenario 3

# Run all scenarios sequentially
uv run python main.py --scenario all
```

---

### 📋 4. Supervisor Inspection & Audit Logs

To view recent authorization requests stored in the IPC database:
```bash
uv run python supervisor_process.py --list
```

---

## 🧪 Running Pytest Tests

Run the full pytest suite verifying the IPC store, app discovery in `adk web`, and cross-process HITL flows:

```bash
uv run pytest tests/test_hitl_adk_web.py -v
```
