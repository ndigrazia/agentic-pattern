# Reasoning and Acting (ReAct) Pattern with Google ADK

An implementation of the **Reasoning and Acting (ReAct)** paradigm ([Yao et al., ICLR 2023](https://arxiv.org/abs/2210.03629)) built on the **Google Agent Development Kit (ADK)** and Gemini models.

This pattern demonstrates how interleaving dynamic internal reasoning traces (`Thought`) with external tool executions (`Action`) and environment feedback (`Observation`) solves complex multi-hop knowledge retrieval, real-time telemetry inspection, and exact arithmetic problems.

---

## Table of Contents

- [What is ReAct?](#what-is-react)
- [ReAct vs. CoT vs. Pure Tool Use](#react-vs-cot-vs-pure-tool-use)
- [Architecture & ReAct Loop](#architecture--react-loop)
- [Tools Included](#tools-included)
- [Quickstart & Setup](#quickstart--setup)
- [Testing on ADK Web (Web UI)](#testing-on-adk-web-web-ui)
- [CLI Demonstration & Modes](#cli-demonstration--modes)
- [Automated Tests](#automated-tests)

---

## What is ReAct?

Large Language Models (LLMs) have strong internal reasoning capabilities, but suffer from two fundamental weaknesses when acting in real-world scenarios:
1. **Hallucination & Stale Facts:** Parametric memory cannot access real-time metrics, internal databases, or private documentation.
2. **Mental Arithmetic Errors:** Complex calculations performed token-by-token often introduce arithmetic drift.

Conversely, agents that call tools blindly without step-by-step reasoning (*pure action*) fail to track subgoals, misinterpret unexpected tool outputs, and cannot backtrack or synthesize multi-source evidence.

**ReAct (Reasoning + Acting)** solves this by synergizing:
- **Reasoning Traces (Thoughts):** The agent decomposes goals, tracks knowns/unknowns, formulates action intent, and analyzes tool returns.
- **Actions:** Targeted tool executions (`search_knowledge_base`, `calculator`, `system_metrics_query`, `database_lookup`).
- **Observations:** Live return values from external systems incorporated back into the agent's context.

---

## ReAct vs. CoT vs. Pure Tool Use

| Dimension | Direct / Zero-Shot | Chain-of-Thought (CoT) | Pure Tool Calling | **ReAct (Reasoning + Acting)** |
| :--- | :--- | :--- | :--- | :--- |
| **External Data** | ❌ None | ❌ None (internal memory) | ✅ Yes (APIs/Tools) | ✅ **Yes (Interactive Environment)** |
| **Multi-Hop Reasoning**| ❌ Weak | ✅ Step-by-step deduction | ❌ Weak / heuristic | ✅ **Interleaved deduction & acting** |
| **Arithmetic Precision**| ⚠️ Prone to hallucination| ⚠️ Better, but prone to math drift| ✅ Tool-dependent | ✅ **Exact (via calculator tool)** |
| **Error Recovery** | ❌ None | ⚠️ Self-correction only | ❌ Vulnerable to bad inputs | ✅ **Observation reflection & retry** |
| **Interpretability** | ❌ Black box | ⚠️ Reasoning only | ⚠️ Actions only | ✅ **Full trace: Thought -> Action -> Obs** |

---

## Architecture & ReAct Loop

```text
User Question
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│ 🧠 1. Thought: Decompose goal, plan next required step      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ ⚡ 2. Action: Call tool with specific parameters             │
│    (search_knowledge_base, system_metrics_query, etc.)       │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 📥 3. Observation: Environment returns ground-truth result   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
                        Need more data?
                        ├── Yes ──> (Loop back to Thought)
                        └── No  ──>
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 🎯 4. Final Answer: Grounded synthesis with citations       │
└─────────────────────────────────────────────────────────────┘
```



---

## Tools Included

The ReAct agent is equipped with 4 production-grade ADK `FunctionTool`s:

1. **`search_knowledge_base(query: str)`**:
   - Searches private enterprise documents, cloud cluster architecture, SLO benchmarks, on-call schedules, and pricing.
2. **`calculator(expression: str)`**:
   - Evaluates math expressions securely with AST recursion (arithmetic, percentages, ratios, math functions).
3. **`system_metrics_query(service_name: str, metric: Optional[str])`**:
   - Queries live telemetry (CPU, memory, latency P99, error rates, pod counts) across microservices (`auth-service`, `billing-api`, `data-pipeline`, `web-gateway`).
4. **`database_lookup(table: str, record_id: str)`**:
   - Queries structured records from tables (`incidents`, `servers`).

---

## Quickstart & Setup

### 1. Environment Configuration

Create or verify `.env` in this directory:

```bash
cd /home/ollama/python/pattern/reasoning-techniques/react
cp ../cot/.env .env
```

Ensure it contains your Gemini credentials:

```bash
GEMINI_MODEL_NAME=gemini-2.5-flash
GOOGLE_API_KEY=your_google_api_key_here
```

### 2. Dependencies

Dependencies are managed using `uv`:

```bash
uv sync
```

---

## Testing on ADK Web (Web UI)

The Google ADK Web UI provides an interactive browser interface to chat with the agent, inspect tool calls in real-time, and trace reasoning trajectories.

### Launching ADK Web

You can launch the ADK Web UI using either of the following commands:

**Option A: Using the convenience launcher**
```bash
uv run python run_web.py --port 8000
```

**Option B: Using the ADK CLI directly**
```bash
uv run adk web . --port 8000 --host 127.0.0.1
```

### Accessing the Web UI

- **Agent Web Interface:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Direct Agent Session:** [http://127.0.0.1:8000/apps/react_agent](http://127.0.0.1:8000/apps/react_agent)
- **Discovered Apps JSON:** [http://127.0.0.1:8000/list-apps](http://127.0.0.1:8000/list-apps)

### Example Prompts to Test in ADK Web

Paste these multi-step queries into the chat box to observe ReAct in action:

1. **Incident Triage & Multi-Hop Query:**
   ```text
   Service 'auth-service' has an alert. Check its current memory utilization, verify if it exceeds the SLO warning threshold from documentation, look up the on-call engineer responsible, and check incident ticket INC-101.
   ```
   *Expected behavior:* The agent queries `system_metrics_query` -> searches `search_knowledge_base` -> queries `database_lookup` -> synthesizes findings.

2. **Cost Difference & Exact Arithmetic:**
   ```text
   Calculate the monthly cost difference between n2-standard-4 and n2-standard-8 compute instances for 720 hours based on documentation pricing.
   ```
   *Expected behavior:* The agent looks up instance prices in `search_knowledge_base` -> invokes `calculator` with `279.36 - 139.68` -> outputs the exact $139.68 difference.

3. **Financial Growth & Target Benchmark:**
   ```text
   From the FY2025 financial documentation, retrieve Q3 and Q4 cloud revenue. Calculate the quarter-over-quarter percentage growth rate, and check whether it exceeded the 15% benchmark target.
   ```



---

## CLI Demonstration & Modes

The CLI runner provides interactive and comparative execution modes:

### 1. Single Query Execution
```bash
uv run python main.py -p "Check memory usage of auth-service and see who is the on-call engineer."
```

### 2. Side-by-Side Comparison (Direct Answering vs. ReAct)
Demonstrates hallucination prevention and exact calculation:
```bash
uv run python main.py -c -p "Calculate the monthly cost difference between n2-standard-4 and n2-standard-8 compute instances for 720 hours."
```

### 3. Benchmark Suite
Runs multi-domain questions:
```bash
uv run python main.py -b
```

### 4. Interactive REPL
```bash
uv run python main.py -i
```

---

## Automated Tests

Run the full pytest suite:

```bash
uv run pytest tests/ -v
```

The test suite covers:
- `test_tools.py`: Unit tests for safe calculator, knowledge base search, live metrics query, and database record lookups.
- `test_react_agent.py`: Agent factories, prompt formatting (zero-shot, few-shot), and deterministic mock runner execution of the ReAct Thought-Action-Observation cycle.
- `test_adk_web.py`: Tests that Google ADK's `AgentLoader` auto-discovers `react_agent` and verifies ADK Web FastAPI endpoints (`/list-apps`, `/apps/react_agent/app-info`, `/`).

