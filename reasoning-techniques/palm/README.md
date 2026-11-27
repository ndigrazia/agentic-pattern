# Program-Aided Language Models (PALM / PAL) - Google ADK

This directory implements the **Program-Aided Language Models (PAL / PALM)** reasoning pattern using the **Google Agent Development Kit (ADK)** (`google-adk`).

---

## 📌 What is Program-Aided Language Models (PAL)?

Program-Aided Language Models (PAL), pioneered by [Gao et al. (2022)](https://arxiv.org/abs/2211.10435), is an advanced reasoning technique designed to overcome the inherent limitations of LLMs in arithmetic, symbolic manipulation, combinatorics, and algorithmic logic.

While standard LLMs struggle with mental calculation and frequently hallucinate numeric answers:
1. **Decomposition into Code**: The model reads natural language problems and formulates executable programs (Python).
2. **Delegation to Interpreter**: Computation is offloaded to a deterministic runtime environment (`BuiltInCodeExecutor`).
3. **Exact Solutions**: Variables, loops, and formulas are computed with 100% precision by the runtime, eliminating arithmetic hallucinations.

---

## 🏗️ Architecture & Multi-Agent Collaboration

The PALM system is structured as a hierarchical multi-agent team:

```
                            User Query
                                │
                                ▼
                   ┌──────────────────────────┐
                   │   RootAgent (PALM)       │
                   │  Orchestrator & Synthesizer
                   └────────────┬─────────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        ▼                                               ▼
┌───────────────────────────────┐       ┌───────────────────────────────┐
│   SearchAgent                 │       │   CodeAgent                   │
│   Tools: [google_search]      │       │   code_executor:              │
│   Specialist in fact-finding  │       │     BuiltInCodeExecutor()     │
│   and real-time web retrieval │       │   Specialist in Python exec   │
└───────────────────────────────┘       └───────────────────────────────┘
```

### Agent Roles:
- **`SearchAgent`**: Equipped with `google_search`. Gathers up-to-date facts, measurements, constants, and external reference data.
- **`CodeAgent`**: Equipped with `BuiltInCodeExecutor`. Writes and executes Python code to solve math, date calculations, counting, and algorithmic tasks.
- **`RootAgent`**: Wraps both sub-agents via `agent_tool.AgentTool`. Decomposes the user prompt, delegates information retrieval to `SearchAgent` and calculations to `CodeAgent`, and synthesizes the verified answer.

---

## 💻 Code Implementation

The agent structure directly implements your requested configuration:

```python
from google.adk.tools import agent_tool
from google.adk.agents import Agent
from google.adk.tools import google_search
from google.adk.code_executors import BuiltInCodeExecutor

search_agent = Agent(
    model='gemini-2.0-flash',
    name='SearchAgent',
    instruction="""
You're a specialist in Google Search
""",
    tools=[google_search],
)

coding_agent = Agent(
    model='gemini-2.0-flash',
    name='CodeAgent',
    instruction="""
You're a specialist in Code Execution
""",
    code_executor=[BuiltInCodeExecutor],
)

root_agent = Agent(
    name="RootAgent",
    model="gemini-2.0-flash",
    description="Root Agent",
    tools=[
        agent_tool.AgentTool(agent=search_agent),
        agent_tool.AgentTool(agent=coding_agent),
    ],
)
```

> **Note on Compatibility**: `palm_agent` automatically normalizes `code_executor=[BuiltInCodeExecutor]` into an initialized `BuiltInCodeExecutor()` instance, and automatically maps `gemini-2.0-flash` to the active model in your environment (`GEMINI_MODEL_NAME=gemini-2.5-flash`), ensuring smooth API execution.

---

## 🌐 Testing with ADK Web UI

You can interactively test the agent using the Google ADK Web interface.

### 1. Launching ADK Web

Run the convenience script:
```bash
python run_web.py
```
Or use the `adk` CLI directly:
```bash
uv run adk web . --host 127.0.0.1 --port 8000
```

### 2. Accessing the Web UI

Open your web browser at:
- **Web UI Session**: [http://127.0.0.1:8000/apps/palm_agent](http://127.0.0.1:8000/apps/palm_agent)
- **Discovered Apps**: [http://127.0.0.1:8000/list-apps](http://127.0.0.1:8000/list-apps)

### 3. Example Queries to Try in ADK Web

1. **High-Precision Math**:
   > *"A principal of $15,000 grows at an annual rate of 6.5% compounded monthly. Write and execute Python code to calculate the balance after 7 years and the total interest earned."*

2. **Algorithmic Simulation**:
   > *"Write and run a Python script to compute the 25th Fibonacci number and check whether it is a prime number."*

3. **Combined Search + Code Execution**:
   > *"Search for the height of Burj Khalifa in meters, then write and run Python code to convert it to feet and miles."*

In the Web UI, you will see `RootAgent` invoke `SearchAgent` to obtain the factual height, then call `CodeAgent` to execute Python conversion code, displaying the results in real-time.

---

## 🖥️ CLI Usage (`main.py`)

Run queries directly from the command line:

```bash
# Run a specific query
uv run python main.py -p "What is 1234 * 5678? Write and run code to calculate it."

# Run the benchmark suite
uv run python main.py -b

# Start an interactive REPL
uv run python main.py -i
```

---

## 🧪 Running Automated Tests

Run the full test suite including live ADK Web server discovery and HTTP endpoints:

```bash
uv run pytest -v
```

