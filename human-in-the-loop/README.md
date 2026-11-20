# Human-in-the-Loop (HITL) Pattern

This directory demonstrates the **Human-in-the-Loop (HITL)** architectural pattern using **Google Agent Development Kit (ADK)** and the Gemini model family.

---

## 🎯 Overview

In autonomous AI agent systems, certain operations carry significant real-world risks or business costs (e.g., escalating to scarce human specialists, issuing high-value hardware replacements, or approving irreversible financial refunds). 

The **Human-in-the-Loop** pattern introduces **confirmation gates** where the agent autonomously decides *what* action needs to take place, but explicitly pauses execution to request authorization from a human operator or supervisor before carrying it out.

### Key Capabilities Demonstrated
1. **Tool Confirmation Gates**: Using Google ADK's native `FunctionTool(..., require_confirmation=True)` to intercept critical tool executions (`escalate_to_human`, `process_replacement_order`).
2. **Context-Aware Personalization**: Dynamic `before_model_callback` injecting customer profiles and previous support history from the session state.
3. **Approval & Rejection Handling**:
   - **Approval**: Supervisor approves the tool execution; agent receives the confirmation payload and completes the task.
   - **Rejection**: Supervisor declines the tool execution; agent gracefully handles the rejection and routes to alternative fallback actions (e.g., creating a standard warranty review ticket).
4. **Automated & Interactive Modes**: Can run automated simulation scenarios or interactive terminal CLI prompts for live operator input.

---

## 🏗️ Architecture

```
                                      +-------------------------+
                                      |      User Prompt        |
                                      +-------------------------+
                                                   |
                                                   v
+------------------------+            +-------------------------+
| Customer Context State | ---------> |   ADK LlmAgent (Gemini) |
+------------------------+            +-------------------------+
                                                   |
                     +-----------------------------+-----------------------------+
                     |                                                           |
                     v                                                           v
        [Routine Diagnostics]                                        [Critical / High-Impact Action]
     `troubleshoot_issue` (Auto)                                     `escalate_to_human` / `process_replacement`
                     |                                                           |
                     v                                                           v
           Direct Tool Response                                        🛑 Confirmation Gate
                                                                           (`adk_request_confirmation`)
                                                                                 |
                                                                                 v
                                                                       👤 [Human Supervisor Review]
                                                                        /                        \
                                                                       /                          \
                                                            ✅ [Approved]                    ❌ [Rejected]
                                                                  |                                |
                                                                  v                                v
                                                      Tool Executes; Case Transferred      Agent Routes to Alternative
                                                      to Human Engineering Queue           (e.g., Standard Review Ticket)
```

---

## 🚀 Getting Started

### 1. Environment Setup

Ensure your `.env` file in this directory or the root contains your Google API credentials:

```bash
GEMINI_MODEL_NAME=gemini-3.8-flash  # or gemini-2.5-flash
GOOGLE_API_KEY=your_gemini_api_key
```

### 2. Running the Scenarios

Run the default scenario (Scenario 2 - Critical Safety Hazard Escalation with Approval):
```bash
uv run python main.py
```

Run specific scenarios:
- **Scenario 1** (Autonomous Routine Diagnostics - No Human Gate):
  ```bash
  uv run python main.py --scenario 1
  ```
- **Scenario 2** (Critical Escalation - Human Supervisor Approves):
  ```bash
  uv run python main.py --scenario 2
  ```
- **Scenario 3** (High-Value Replacement - Human Supervisor Rejects & Agent Fallbacks):
  ```bash
  uv run python main.py --scenario 3
  ```
- **All Scenarios**:
  ```bash
  uv run python main.py --scenario all
  ```

### 3. Interactive CLI Mode

To act as the human supervisor in real time via the command line:
```bash
uv run python main.py --interactive
```
When an approval gate is triggered, the runner prompts:
```
👉 Human decision - Approve this action? [y/N]:
```

