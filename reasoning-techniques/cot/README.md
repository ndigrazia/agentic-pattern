# Chain-of-Thought (CoT) Reasoning Pattern (Google ADK)

This directory implements the **Chain-of-Thought (CoT) Reasoning Technique** for AI agents using the **Google Agent Development Kit (ADK)** (`google-adk`).

---

## 📌 What is Chain-of-Thought (CoT) Reasoning?

Chain of Thought (CoT), introduced by [Wei et al. (2022)](https://arxiv.org/abs/2201.11903), is a foundational reasoning technique that prompts large language models to break down complex multi-step problems into explicit, sequential intermediate reasoning steps ("thought chains") before arriving at a final solution.

Unlike traditional direct prompting—which frequently fails on multi-step arithmetic, symbolic logic, and constraint satisfaction problems—Chain-of-Thought reasoning:
1. **Prevents Premature Conclusions**: Forces the agent to allocate reasoning tokens to premise decomposition and intermediate deductions.
2. **Improves Auditability & Transparency**: Users and downstream systems can verify each step of the deduction chain rather than accepting a black-box answer.
3. **Enables Tool Integration During Thought Steps**: Allows the agent to invoke tools (such as mathematical calculators or code executors) during intermediate computation stages.
4. **Supports Multi-Agent Verification**: Reasoning steps can be handed off to dedicated verifier or auditor agents for independent validation.

---

## 🏗️ Architecture & Implementation in Google ADK

This package provides two complementary architectures for Chain-of-Thought reasoning within the Google ADK ecosystem:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                   Google ADK Chain-of-Thought Framework                  │
└──────────────────────────────────────────────────────────────────────────┘

1. Single-Agent CoT (Zero-Shot / Few-Shot)
   User Query ──► [ cot_agent (LlmAgent) ] ──► [ calculate Tool ] ──► Response
                     ├─ Phase 1: Problem Decomposition
                     ├─ Phase 2: Step-by-Step Chain of Thought
                     ├─ Phase 3: Sanity Check & Verification
                     └─ Phase 4: Authoritative Final Answer

2. Two-Stage Multi-Agent Workflow (Reasoner -> Verifier Pipeline)
   User Query ──► [ START ]
                     │
                     ▼
         [ CoTReasoner Agent ] ──► session.state["reasoning_chain"]
                     │
                     ▼
         [ CoTVerifier Agent ] ──► session.state["verified_answer"]
                     │
                     ▼
             Final Verified Answer
```

### 1. Single-Agent CoT (`cot_agent/agent.py`)
- Employs an ADK `LlmAgent` configured with a 4-phase reasoning protocol (`Problem Decomposition`, `Step-by-Step Chain of Thought`, `Verification & Sanity Check`, and `Final Answer`).
- Equipped with the `calculate` tool (`FunctionTool`) for safe, deterministic mathematical evaluation during deduction steps.
- Exposes `root_agent` for native **Google ADK Web UI** discovery and serving.

### 2. Two-Stage Multi-Agent Workflow (`cot_agent/workflow.py`)
- **Stage 1 (`CoTReasoner`)**: Formulates the problem equations, extracts premises, and generates intermediate deductions, saving them to `session.state["reasoning_chain"]`.
- **Stage 2 (`CoTVerifier`)**: Audits each step for logical fallacies or arithmetic errors, verifies constraint adherence, and issues the certified final answer in `session.state["verified_answer"]`.
- Orchestrated via `google.adk.workflow.Workflow` using directed dependency edges.

---

## 📂 Directory Structure

```
pattern/reasoning-techniques/cot/
├── .env                              # Environment variables (GEMINI_MODEL_NAME, GOOGLE_API_KEY)
├── pyproject.toml                    # UV workspace package dependencies
├── README.md                         # Documentation & pattern guide
├── run_web.py                        # ADK Web launcher script
├── main.py                           # CLI demonstration runner & benchmark tool
├── cot_agent/                        # Core ADK Agent package
│   ├── __init__.py                   # Package exports
│   ├── agent.py                      # LlmAgent definition & root_agent export for ADK Web
│   ├── prompts.py                    # Zero-shot, Few-shot exemplars, & system instructions
│   ├── tools.py                      # Safe mathematical AST calculator tool
│   └── workflow.py                   # Two-stage Workflow (Reasoner -> Verifier)
└── tests/                            # Comprehensive Pytest test suite
    ├── test_adk_web.py               # ADK Web discovery & agent property tests
    ├── test_cot_agent.py             # Agent initialization, few-shot modes, & mock execution
    ├── test_cot_workflow.py          # Workflow execution, state retention, & verification
    └── test_tools.py                 # Math tool validation, safety, & injection prevention
```


---

## 🚀 Quickstart & Setup

### 1. Environment Configuration

Ensure your `.env` file contains your Google Gemini API key:

```bash
GEMINI_MODEL_NAME=gemini-2.5-flash
GOOGLE_API_KEY=your_api_key_here
```

### 2. Dependency Installation

The project uses `uv` for lightning-fast workspace package management:

```bash
cd /home/ollama/python/pattern/reasoning-techniques/cot
uv sync
```

---

## 💻 CLI Usage

The `main.py` script provides versatile execution options:

### 1. Solve a Reasoning Problem (Zero-Shot CoT)
```bash
uv run python main.py -p "If a train travels 60 mph for 2.5 hours and 40 mph for 1.5 hours, what is its average speed?"
```

### 2. Few-Shot Exemplar Reasoning
```bash
uv run python main.py -m few-shot -p "A farmer has 15 cows and chickens in total with 46 legs. How many cows and chickens are there?"
```

### 3. Two-Stage Workflow (Reasoner -> Verifier Pipeline)
```bash
uv run python main.py -m workflow -p "Solve the system: 3x + 2y = 16 and x - y = 2."
```

### 4. Side-by-Side Comparison: Direct Answering vs CoT
Demonstrates how Direct Answering (without scratchpad) compares to Chain-of-Thought reasoning:
```bash
uv run python main.py --compare -p "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost?"
```

### 5. Multi-Domain Benchmark Suite
Runs reasoning benchmarks across arithmetic word problems, constraint logic, and algorithmic traces:
```bash
uv run python main.py --benchmark
```

### 6. Interactive REPL Mode
```bash
uv run python main.py -i
```

---

## 🌐 Google ADK Web UI Integration

The CoT agent is fully integrated with Google ADK Web UI.

Start the web server:
```bash
uv run python run_web.py
```
Or directly using ADK CLI:
```bash
uv run adk web . --host=127.0.0.1 --port=8000
```

Open your browser to:
- **ADK Web UI**: `http://127.0.0.1:8000`
- **Direct Agent Chat**: `http://127.0.0.1:8000/apps/cot_agent`
- **Application List Endpoint**: `http://127.0.0.1:8000/list-apps`

---

## 🧪 Running Tests

Execute the comprehensive test suite with `pytest`:

```bash
uv run pytest -v
```

The test suite covers:
- Safe AST math evaluation, division by zero handling, and code injection protection (`test_tools.py`).
- Single-agent zero-shot and few-shot CoT initialization and mock streaming (`test_cot_agent.py`).
- Two-stage Reasoner -> Verifier workflow execution and session state persistence (`test_cot_workflow.py`).
- Google ADK Web agent discovery and interface compatibility (`test_adk_web.py`).

