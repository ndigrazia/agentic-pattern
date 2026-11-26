# Resource-Aware Optimization Pattern (Google ADK)

This directory implements the **Resource-Aware Optimization Pattern** for AI agents using the **Google Agent Development Kit (ADK)** (`google-adk`).

---

## Pattern Overview

In LLM multi-agent architectures, using a high-capacity model (such as Gemini Pro) for simple questions wastes compute, creates unnecessary inference latency, and strains token budgets. Conversely, relying solely on lightweight models (such as Gemini Flash) can degrade reasoning quality for multi-step architecture design, mathematical proofs, or complex algorithm refactoring.

The **Resource-Aware Optimization Pattern** dynamically analyzes the complexity and resource demands of incoming user requests before routing execution to the most cost-effective and capable agent tier.

### Key Benefits

- **Cost Efficiency**: Achieves ~85–90% reduction in token costs by resolving straightforward queries on the lightweight tier.
- **Latency Optimization**: Lightweight queries return in 1–3 seconds instead of 10+ seconds.
- **Capacity Preservation**: Preserves high-capacity models and quotas for tasks requiring deep reasoning, complex system design, or large token outputs.
- **Observability**: Records routing rationale, complexity scores, token metrics, and execution latency directly into the ADK session state.

---

## Architecture

```
                                    ┌───────────────────────┐
                                    │      User Query       │
                                    └───────────┬───────────┘
                                                │
                                    ┌───────────▼───────────┐
                                    │    QueryRouterAgent   │
                                    │     (google.adk)      │
                                    └───────────┬───────────┘
                                                │
                         ┌──────────────────────┴──────────────────────┐
                         ▼                                             ▼
            [Score < Threshold: 0.50]                     [Score >= Threshold: 0.50]
        ⚡ Lightweight Resource Tier                    🧠 High-Capacity Resource Tier
       ┌───────────────────────────────┐              ┌───────────────────────────────┐
       │       GeminiFlashAgent        │              │        GeminiProAgent         │
       │     (gemini-2.5-flash)        │              │       (gemini-2.5-pro)        │
       │                               │              │                               │
       │ - Fast inference (< 3s)       │              │ - Deep analytical reasoning   │
       │ - ~85-90% cost savings        │              │ - Architecture & algorithm    │
       │ - Concise, accurate answers   │              │ - Controlled thinking budget  │
       └───────────────┬───────────────┘              └───────────────┬───────────────┘
                       │                                              │
                       └──────────────────────┬───────────────────────┘
                                              │
                                    ┌─────────▼──────────┐
                                    │    ADK Session     │
                                    │   State & Events   │
                                    │ (Telemetry/Metrics)│
                                    └────────────────────┘
```

---

## Complexity Evaluation Engine

The query complexity analyzer evaluates requests across four dimensions to produce a calibrated score between `0.0` and `1.0`:

1. **Word & Token Density**:
   - Short (< 15 words): base score `0.05`
   - Moderate (15–60 words): `0.15` to `0.30`
   - Extensive (> 60 words): `0.45`
2. **Domain Complexity Keywords**: Detects terms requiring deep technical reasoning (e.g., `architecture`, `consensus`, `microservices`, `deadlock`, `distributed`, `sharding`, `trade-offs`, `optimize`, `audit`).
3. **Code & Syntax Indicators**: Detects Markdown code blocks (` ``` `), SQL statements, and programming syntax (`def `, `class `, `import `, `async def `).
4. **Multi-Part Structure**: Identifies multiple question marks (`?`), numbered lists, or multi-step requirement specifications.

If `score >= complexity_threshold` (default `0.50`), the query routes to `GeminiProAgent`. Otherwise, it routes to `GeminiFlashAgent`.

## File Structure

- `optimization_agent/`: Core Agent and ADK Web application package:
  - `router_agent.py`: Agent logic, complexity heuristics, `QueryRouterAgent`, and `ResourceTier` models.
  - `agent.py`: Exposes `root_agent` for Google ADK Web auto-discovery.
  - `__init__.py`: Package exports for `root_agent` and router components.
- `main.py`: Application CLI driver and execution helper:
  - `run_query(...)`: Runner orchestrating execution via `InMemoryRunner` and collecting metrics.
  - `run_demo(...)`: Multi-query automated demonstration suite.
  - `interactive_mode(...)`: Interactive REPL for real-time prompt testing.
  - CLI parser for `--prompt`, `--threshold`, `--demo`, and `--interactive`.
- `run_web.py`: Convenience launcher starting the native Google ADK Web UI server.
- `prove_adk_web.py`: Automated end-to-end proof running queries against the live ADK Web server.
- `pyproject.toml`: Dependencies and pytest configuration.
- `.env`: Environment variables (`GOOGLE_API_KEY`, `FLASH_MODEL_NAME`, `PRO_MODEL_NAME`).
- `tests/`: Test suite:
  - `test_router.py`: Unit tests for scoring heuristics, thresholds, and routing delegation.
  - `test_adk_web.py`: Verifies ADK Web app discovery and agent export contracts.

---

## Configuration

Set your Gemini API key in `.env`:

```bash
GOOGLE_API_KEY="your_gemini_api_key"
FLASH_MODEL_NAME="gemini-2.5-flash"
PRO_MODEL_NAME="gemini-2.5-pro"
```

---

## Usage

### 1. Interactive Web UI (`adk web`)

Launch the Google ADK browser-based Web UI:

```bash
cd /home/ollama/python/pattern/resource-aware-optimization
uv run python run_web.py
```
*(Or directly using ADK CLI: `uv run adk web . --port=8000`)*

Then open your browser:
- **Web UI:** [http://localhost:8000](http://localhost:8000)
- **Direct Agent Chat:** [http://localhost:8000/apps/optimization_agent](http://localhost:8000/apps/optimization_agent)
- **Discovered Apps:** [http://localhost:8000/list-apps](http://localhost:8000/list-apps)

### 2. Run the Automated ADK Web Proof

Verifies that the live ADK Web server correctly discovers `optimization_agent` and routes queries over HTTP:

```bash
uv run python prove_adk_web.py
```

### 3. Run the Multi-Query Demo Suite (CLI)

Executes simple, moderate, and complex queries and outputs a comparative allocation table:

```bash
uv run python main.py --demo
```

### 4. Run a Single Prompt

```bash
uv run python main.py --prompt "What is the speed of light in vacuum?"
```

Or a complex architectural query:

```bash
uv run python main.py --prompt "Design a distributed consensus mechanism with Byzantine fault tolerance and analyze network partition trade-offs."
```

### 5. Adjust the Routing Threshold

Route more aggressively to Pro by lowering the threshold:

```bash
uv run python main.py --prompt "Compare SQL vs NoSQL" --threshold 0.2
```

### 6. Interactive REPL Mode (Terminal)

Test queries interactively with real-time routing metrics:

```bash
uv run python main.py --interactive
```

### 7. Programmatic API

```python
import asyncio
from main import run_query

async def example():
    result = await run_query("What is 10 + 25?")
    print("Agent:", result["executing_agent"])
    print("Tier:", result["complexity_analysis"].tier.value)
    print("Latency:", result["elapsed_seconds"], "s")

asyncio.run(example())
```


---

## Example Prompts: Flash vs Pro

The complexity analyzer scores queries from `0.0` to `1.0`. Queries with a score `< 0.50` route to **Gemini Flash**, while queries with a score `≥ 0.50` route to **Gemini Pro**.

### ⚡ Prompts that Route to Gemini Flash (Lightweight Tier)

Flash is selected for simple, factual, and low-cognitive-load queries:

| Prompt | Score | Rationale |
| :--- | :--- | :--- |
| `"What is the boiling point of water in Celsius?"` | `0.05` | Short factual query (< 15 words) |
| `"Briefly explain what a Python dictionary is in two sentences."` | `0.05` | Straightforward definition |
| `"What is 15 * 28?"` | `0.05` | Simple math calculation |
| `"Translate 'Good morning, how are you?' to Spanish and French."` | `0.15` | Basic multilingual translation |

```bash
uv run python main.py --prompt "What is the capital of Japan?"
```

---

### 🧠 Prompts that Route to Gemini Pro (High-Capacity Tier)

Pro is allocated when queries involve system architecture, distributed algorithms, multi-step optimization, or formal proofs:

#### 1. Distributed Event Streaming & Consensus Architecture
```text
Design a fault-tolerant, high-throughput distributed event streaming architecture using Kafka, database sharding, and consensus protocols. Analyze the trade-offs between strict consistency and availability under network partitions, and provide a step-by-step optimization plan for sub-10ms latency.
```
* **Score:** `0.75` (High length + keywords: `architecture`, `distributed`, `consensus`, `sharding`, `trade-offs`, `optimize`)
* **Execution:**
  ```bash
  uv run python main.py --prompt "Design a fault-tolerant, high-throughput distributed event streaming architecture using Kafka, database sharding, and consensus protocols. Analyze the trade-offs between strict consistency and availability under network partitions, and provide a step-by-step optimization plan for sub-10ms latency."
  ```

#### 2. Concurrency, Deadlock & Algorithm Optimization
```text
Analyze the time and space complexity of this distributed consensus algorithm. Provide a mathematical proof and refactor the code to eliminate deadlocks and race conditions under concurrent workloads.
```
* **Score:** `0.60` (Keywords: `algorithm`, `time complexity`, `space complexity`, `deadlock`, `race condition`, `concurrency`, `mathematical proof`)
* **Execution:**
  ```bash
  uv run python main.py --prompt "Analyze the time and space complexity of this distributed consensus algorithm. Provide a mathematical proof and refactor the code to eliminate deadlocks and race conditions under concurrent workloads."
  ```

#### 3. Security & System Architecture Audit
```text
Perform an architectural audit of a microservices authentication flow using OAuth2 and mTLS. Detail the trade-offs between centralized session state and stateless JWTs, and identify potential attack vectors.
```
* **Score:** `0.60` (Keywords: `architectural`, `audit`, `microservices`, `trade-offs`)
* **Execution:**
  ```bash
  uv run python main.py --prompt "Perform an architectural audit of a microservices authentication flow using OAuth2 and mTLS. Detail the trade-offs between centralized session state and stateless JWTs, and identify potential attack vectors."
  ```

---

## Running Unit Tests

Run the test suite using `uv`:

```bash
cd /home/ollama/python/pattern/resource-aware-optimization
uv run pytest -v
```


