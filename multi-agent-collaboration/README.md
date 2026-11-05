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

- `adk_executor.py`: Core implementation of `Greeter`, `TaskExecutor`, `Coordinator`, sequential workflow, and runner helpers.
- `adk_looper.py`: Cyclic loop workflow pattern using `Workflow`, `LlmAgent` (`ProcessingStep`), `ConditionChecker`, and `CompletionStep` with state inspection tools and conditional route transitions.
- `pyproject.toml`: Dependencies.
- `.env`: Environment variables (`GEMINI_MODEL_NAME`, `GOOGLE_API_KEY`).

---

## How to Run

### 1. Execute Loop Pattern (`adk_looper.py`)
Runs the iterative agent loop (`StatusPoller`) with `ProcessingStep` and `ConditionChecker`:

```bash
cd ~/python/pattern/multi-agent-collaboration
uv run python adk_looper.py
```

Or pass a custom prompt:
```bash
uv run python adk_looper.py "Run a 3-step pipeline and set status to completed on step 3."
```

### 2. Execute Multi-Agent Collaboration Suite (`adk_executor.py`)
Runs `Greeter` individually, `TaskExecutor` individually, and both collaboratively via `Coordinator`:

```bash
cd ~/python/pattern/multi-agent-collaboration
uv run python adk_executor.py
```

#### Individual Agent Execution:
```bash
uv run python adk_executor.py greeter
uv run python adk_executor.py task
uv run python adk_executor.py coordinator
uv run python adk_executor.py workflow
```

