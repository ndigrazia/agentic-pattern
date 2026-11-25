# Multi-Agent Agent-to-Agent (A2A) Pattern with Google ADK Web and Gemini

This pattern demonstrates a complete multi-agent architecture where **two Google ADK agents communicate using the A2A (Agent-to-Agent) protocol**, testable directly inside the **Google ADK Web UI (`adk web`)** using **Gemini LLM**.

---

## 🏗️ Architecture

```
                                    GOOGLE ADK WEB UI
                                  (http://localhost:8000)
                                            │
                                            │ (User Chat / REST API)
                                            ▼
                             ┌─────────────────────────────┐
                             │     coordinator_agent       │
                             │        (Gemini LLM)         │
                             └──────────────┬──────────────┘
                                            │
                                            │ A2A Protocol (JSON-RPC over HTTP)
                                            │ http://localhost:8000/a2a/math_agent
                                            ▼
                             ┌─────────────────────────────┐
                             │         math_agent          │
                             │ (Remote A2A Agent + Gemini) │
                             │  - Tools: add, multiply,    │
                             │    power, factorial         │
                             └─────────────────────────────┘
```

1. **`coordinator_agent` (Primary Orchestrator):**
   - Served in the ADK Web UI (`/apps/coordinator_agent`).
   - Powered by **Gemini** (`gemini-3.8-flash`).
   - Delegates any mathematical questions, equations, or calculations to `math_agent` using ADK's native `RemoteA2aAgent`.

2. **`math_agent` (Specialized A2A Agent):**
   - Exposes standard A2A endpoints and discovery card (`/a2a/math_agent/.well-known/agent-card.json`).
   - Powered by **Gemini** (`gemini-3.8-flash`) with dedicated Python computation tools: `add`, `multiply`, `power`, and `factorial`.
   - Executes calculations and returns structured A2A responses to `coordinator_agent`.

---

## 📁 Project Structure

```
pattern/a2a-2/
├── .env                          # Gemini API Key & model configuration
├── pyproject.toml                # UV project configuration and dependencies
├── README.md                     # Documentation
├── registry.py                   # A2A Agent Registry CLI & Client
├── registry.json                 # Persistent registry database of A2A agents
├── run_web.py                    # Convenience launcher for ADK Web with A2A enabled
├── example.py                    # CLI script to verify A2A communication
├── coordinator_agent/
│   ├── __init__.py               # Exports root_agent
│   └── agent.py                  # Primary agent with RemoteA2aAgent sub-agent
├── math_agent/
│   ├── __init__.py               # Exports root_agent
│   ├── agent.json                # A2A Agent Card specification
│   └── agent.py                  # Specialist math agent with computation tools
└── tests/
    └── test_a2a.py               # Automated pytest suite
```

---

## 🚀 Getting Started

### 1. Prerequisites

Ensure `GOOGLE_API_KEY` is configured in `.env` (or inherited from root):
```bash
GEMINI_MODEL_NAME=gemini-3.8-flash
GOOGLE_API_KEY=your_api_key_here
```

### 2. Start ADK Web with A2A Support

From the repository root:
```bash
uv run adk web --a2a --port=8000 pattern/a2a-2
```
Or run the launcher script:
```bash
uv run python pattern/a2a-2/run_web.py
```

You will see:
```
Setting up A2A agent: math_agent
Successfully configured A2A agent: math_agent
ADK Web Server started at http://127.0.0.1:8000
```

---

## 🧪 Testing the Agents

### Option 1: In the Browser via ADK Web UI

1. Open your browser at **`http://localhost:8000`**.
2. Select **`coordinator_agent`** from the top app selector.
3. Start a conversation with a mathematical prompt, for example:
   - *"What is 25 multiplied by 14?"*
   - *"Calculate 2 to the power of 10 and then calculate 6 factorial."*
4. In the chat UI, you will see `coordinator_agent` invoke `math_agent` via A2A, execute the calculation, and present the final answer.

### Option 2: Automated CLI Verification

While the ADK Web server is running, execute in another terminal:
```bash
# Default prompt
uv run python pattern/a2a-2/example.py


---

## 📋 A2A Agent Registry

The `registry.py` module provides dynamic registration, discovery, and management of A2A agents so that agents do not need hardcoded URLs.

### Using the Registry CLI

```bash
# 1. Register an agent from a local agent.json file
uv run python registry.py register --file math_agent/agent.json

# 2. Register an agent from a live A2A URL endpoint
uv run python registry.py register --url http://localhost:8000/a2a/math_agent

# 3. List all registered agents
uv run python registry.py list

# 4. Search agents by skill tag or keyword
uv run python registry.py search math

# 5. Unregister an agent
uv run python registry.py unregister math_agent
```

### Programmatic Usage in Python

```python
from registry import A2AAgentRegistry

registry = A2AAgentRegistry()

# Register an agent
registry.register(file_path="math_agent/agent.json")

# Find agents with a specific skill
agents = registry.search("math")

# Create a Google ADK RemoteA2aAgent dynamically from the registry entry
remote_agent = registry.create_remote_agent("math_agent")
```

# Custom prompt
uv run python pattern/a2a-2/example.py "What is 125 multiplied by 4? Use math_agent."
```

### Option 3: Inspect the A2A Agent Card Directly

```bash
curl http://localhost:8000/a2a/math_agent/.well-known/agent-card.json
```

### Option 4: Run Unit Tests

```bash
cd pattern/a2a-2 && uv run pytest
```

