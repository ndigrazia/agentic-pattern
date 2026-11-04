# Multi-Agent Collaboration Pattern (Google ADK)

This directory implements the **Multi-Agent Collaboration Pattern** using the **Google Agent Development Kit (ADK)** (`google-adk`).

---

## Pattern Overview

The Multi-Agent Collaboration Pattern coordinates specialized agents with distinct responsibilities:
1. **`Greeter` (`LlmAgent`)**: Greets the user, establishes friendly rapport, and introduces the team.
2. **`TaskExecutor` (Custom `BaseAgent`)**: Performs deterministic computational tasks, collects system telemetry, and stores structured results into shared session state.
3. **`Coordinator` (`LlmAgent`)**: Central orchestrator that routes user requests and delegates to `Greeter`, `TaskExecutor`, or both.
4. **`collaboration_workflow` (`Workflow`)**: Direct sequential pipeline connecting `Greeter -> TaskExecutor`.

---

## File Structure

- `adk.py`: Core implementation of `Greeter`, `TaskExecutor`, `Coordinator`, and runner helpers.
- `main.py`: Entrypoint delegating to `adk.py`.
- `pyproject.toml`: Dependencies.
- `.env`: Environment variables (`GEMINI_MODEL_NAME`, `GOOGLE_API_KEY`).

---

## How to Run

### 1. Execute Both Agents (Complete Demonstration)
Runs `Greeter` individually, `TaskExecutor` individually, and both collaboratively via `Coordinator`:

```bash
cd ~/python/pattern/multi-agent-collaboration
uv run python adk.py
```

or:

```bash
uv run python main.py
```

### 2. Execute Only the Greeter Agent
```bash
uv run python adk.py greeter
```

### 3. Execute Only the TaskExecutor Agent
```bash
uv run python adk.py task
```

### 4. Execute Both Agents via Coordinator Delegation
```bash
uv run python adk.py coordinator
```

### 5. Execute Both Agents via Sequential Workflow Pipeline
```bash
uv run python adk.py workflow
```

