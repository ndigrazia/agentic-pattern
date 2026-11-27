# Self-Correction Reasoning Pattern (Google ADK)

This directory implements the **Self-Correction Reasoning Technique** for AI agents using the **Google Agent Development Kit (ADK)** (`google-adk`).

---

## 📌 What is Self-Correction Reasoning?

**Self-Correction** is an advanced cognitive reasoning pattern where an AI agent acts as a critical, detail-oriented reviewer of previously generated content. Rather than accepting an initial output as final, the agent systematically audits the draft against the original prompt requirements, identifies specific discrepancies and weaknesses, proposes actionable solutions, and iteratively rewrites the text into an accurate, complete, engaging, and constraint-compliant revision.

### The 5-Step Systematic Self-Correction Process:
1. **Understand Original Requirements:** Review the initial prompt and specifications that led to the content's creation. What was the *original intent*? What are key constraints (e.g., character limits, format, mandatory elements, target audience)?
2. **Analyze Current Content:** Read the provided draft carefully and objectively. Measure length, character/word counts, and examine sentence structure.
3. **Identify Discrepancies/Weaknesses:** Compare the current draft against the original requirements across six core dimensions:
   - **Accuracy Issues:** Are there any factual errors or misleading statements?
   - **Completeness Gaps:** Does it fully address all aspects of the original prompt? Is anything missing?
   - **Clarity & Coherence:** Is the language clear, concise, and easy to understand? Does it flow logically?
   - **Tone & Style:** Does it match the desired tone and style (e.g., professional, engaging, concise)?
   - **Engagement:** Is it captivating? Does it hold the reader's attention?
   - **Redundancy/Verbosity:** Can any parts be condensed or removed without losing meaning?
4. **Propose Specific Improvements:** For each identified weakness, suggest concrete and actionable changes. Do not just state the problem; propose a solution.
5. **Generate Revised Content:** Based on the proposed improvements, rewrite the original content to incorporate all necessary changes. Ensure the revised content is polished, verified against constraints, and ready for final use.

---

## 🎯 Case Study: GreenTech Gadgets Launch

The agent embodies the systematic process demonstrated on the following canonical case study:

- **Original Prompt/Requirements:**
  > "Write a short, engaging social media post (max 150 characters) announcing a new eco-friendly product line: 'GreenTech Gadgets'."

- **Initial Draft (Content to be corrected):**
  > "We have new products. They are green and techy. Buy GreenTech Gadgets now!" *(64 characters)*

- **Self-Correction Agent's Thought Process (Internal CoT Output):**
  - **Thought 1 (Understand Original Requirements):**
    - Short, engaging social media post.
    - Max 150 characters.
    - Announce "GreenTech Gadgets" - a new eco-friendly product line.
  - **Thought 2 (Analyze Current Content):**
    - `"We have new products. They are green and techy. Buy GreenTech Gadgets now!"` (64 characters)
  - **Thought 3 (Identify Discrepancies/Weaknesses):**
    - **Engaging:** Not very engaging. Sounds generic.
    - **Eco-friendly:** Implied by "green," but not explicitly highlighted as a benefit.
    - **Call to Action:** "Buy now!" is okay, but could be more compelling.
    - **Conciseness:** It's short, but could use stronger verbs/phrasing.
    - **Impact:** Lacks excitement for a new product launch.
  - **Thought 4 (Propose Specific Improvements):**
    - Make it more dynamic and exciting.
    - Emphasize "eco-friendly" and "innovation."
    - Use stronger verbs and more active voice.
    - Add a clear, engaging call to action.
    - Ensure it stays under 150 characters.
  - **Thought 5 (Generate Revised Content):**
    - Original: `"We have new products. They are green and techy. Buy GreenTech Gadgets now!"`
    - Revised idea: `"🌱 Discover GreenTech Gadgets! Our new eco-friendly line blends innovation with sustainability. Go green, go smart! Shop now! #EcoFriendly #GreenTech"` (148 characters)
    - *Tool Verification*: Metric tools verify 148 chars <= 150 constraint and required keywords present.

- **Self-Correction Agent's Final Revised Content (Output to User):**
  > `🌱 Discover GreenTech Gadgets! Our new eco-friendly line blends innovation with sustainability. Go green, go smart! Shop now! #EcoFriendly #GreenTech`

---


## 🏗️ Architecture & Implementation in Google ADK

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                  Google ADK Self-Correction Agent Pattern                    │
└──────────────────────────────────────────────────────────────────────────────┘

1. Standalone Self-Correction Agent (ADK Web UI & CLI)
   Requirements + Draft ──► [ self_correction_agent (LlmAgent) ]
                                    │
                                    ├─ Thought 1: Understand Requirements
                                    ├─ Thought 2: Analyze Content ──► [ analyze_text_metrics Tool ]
                                    ├─ Thought 3: Identify Weaknesses (6 Dimensions)
                                    ├─ Thought 4: Propose Solutions
                                    └─ Thought 5: Generate Revision ──► [ verify_constraint_checklist ]
                                    │
                                    ▼
                         Polished Final Output

2. Two-Stage Autonomous Workflow Pipeline
   Requirements ──► [ START ]
                        │
                        ▼
               [ DraftWriter Agent ] ──► session.state["draft_content"]
                        │
                        ▼
         [ SelfCorrectionCritic Agent ] ──► session.state["corrected_content"]
                        │
                        ▼
               Final Verified Content
```

### Components
- **`self_correction_agent/agent.py`**: Exports `root_agent` for Google ADK Web UI and provides `create_self_correction_agent()`.
- **`self_correction_agent/prompts.py`**: Encapsulates the 5-step systematic instructions, formatting protocols, and few-shot exemplars.
- **`self_correction_agent/tools.py`**: ADK FunctionTools for deterministic constraint verification (`analyze_text_metrics`, `verify_constraint_checklist`).
- **`self_correction_agent/workflow.py`**: Multi-agent workflow connecting a generator (`DraftWriter`) to the reviewer (`SelfCorrectionCritic`).
- **`compare.py`**: Dedicated script for side-by-side comparison of the Standalone Agent vs Multi-Agent Workflow.
- **`run_web.py`**: Launcher script for the Google ADK Web UI.
- **`main.py`**: CLI demonstration runner with benchmark, workflow, comparison, and interactive modes.

---

## ⚖️ Standalone Agent vs Multi-Agent Workflow

This pattern demonstrates two distinct implementation approaches:

| Feature / Metric | Alternative 1: Standalone Agent (`self_correction_agent`) | Alternative 2: Workflow Pipeline (`self_correction_pipeline`) |
| :--- | :--- | :--- |
| **Architecture** | Single `LlmAgent` | Multi-agent DAG (`Workflow`) |
| **Input Required** | **Both** Prompt Requirements + Existing Draft | **Only** Prompt Requirements |
| **Draft Origin** | Supplied by human / external client | Generated autonomously by `DraftWriter` |
| **Agent Nodes** | 1 (`self_correction_agent`) | 2 (`DraftWriter` ➔ `SelfCorrectionCritic`) |
| **Session State** | In-prompt / ephemeral context | Stored in `session.state["draft_content"]` & `session.state["corrected_content"]` |
| **Execution Graph** | Single agent node | Directed edges: `(START, DraftWriter)` and `(DraftWriter, SelfCorrectionCritic)` |
| **ADK Web UI Integration** | Exposed as default `root_agent` for chat | Discovered as a multi-step pipeline |
| **Primary Use Case** | User has a draft in hand and wants AI feedback/editing | Fully automated generation + self-correction pipeline |

### Understanding the Workflow Graph (`workflow.py`)

In `self_correction_agent/workflow.py`, the workflow is defined as:

```python
pipeline = Workflow(
    name=name,
    edges=[
        (START, generator_agent),
        (generator_agent, critic_agent),
    ],
    description="Two-stage Self-Correction workflow: DraftWriter creates draft, SelfCorrectionCritic refines it.",
)
```

1. **`START` Sentinel**: Special ADK entrypoint from `google.adk.workflow`. Indicates that initial incoming requests route immediately to `generator_agent` (`DraftWriter`).
2. **Sequential Edges `(generator_agent, critic_agent)`**: Defines the transition. Once `generator_agent` finishes, the runtime advances automatically to `critic_agent` (`SelfCorrectionCritic`).
3. **Automated State Hand-off**:
   - `generator_agent` defines `output_key="draft_content"`, so its output is saved into `session.state["draft_content"]`.
   - `critic_agent` defines `{draft_content}` in its instruction prompt, which ADK automatically populates from session state before invoking the critic.

---

## 📂 Directory Structure

```
pattern/reasoning-techniques/self-correction/
├── .env                             # Environment configuration (GEMINI_MODEL_NAME, GOOGLE_API_KEY)
├── pyproject.toml                   # UV package definition and dependencies
├── README.md                        # Documentation & pattern guide
├── run_web.py                       # ADK Web UI convenience launcher
├── main.py                          # CLI demonstration runner & benchmark tool
├── compare.py                       # Side-by-side comparison runner (Agent vs Workflow)
├── self_correction_agent/           # Core ADK Agent package
│   ├── __init__.py                  # Package exports (root_agent, create functions, tools)
│   ├── agent.py                     # LlmAgent definition & root_agent export for ADK Web
│   ├── prompts.py                   # System instructions, 5-step protocol & few-shot exemplars
│   ├── tools.py                     # Metric analysis & constraint checklist FunctionTools
│   └── workflow.py                  # Two-stage Workflow (DraftWriter -> SelfCorrectionCritic)
└── tests/                           # Pytest test suite
    ├── test_adk_web.py              # ADK Web discovery, root_agent export, & live HTTP tests
    ├── test_agent.py                # Agent configuration & mock execution tests
    ├── test_workflow.py             # Multi-agent workflow execution tests
    └── test_tools.py                # Metric calculation & constraint checker tests
```

---

## 🚀 Quickstart & Setup

### 1. Environment Configuration

Ensure your `.env` file contains your Google Gemini configuration:

```bash
GEMINI_MODEL_NAME=gemini-2.5-flash
GOOGLE_API_KEY=your_api_key_here
```

### 2. Dependency Installation

Sync dependencies using `uv`:

```bash
cd /home/ollama/python/pattern/reasoning-techniques/self-correction
uv sync
```

---

## 🌐 Testing with ADK Web

The package natively exports `root_agent` for the Google Agent Development Kit Web UI.

### Option A: Using `run_web.py`
```bash
uv run python run_web.py --port=8000
```

### Option B: Using the `adk` CLI directly
```bash
uv run adk web . --port=8000
```

### Accessing the Web UI:
- **Web Browser Interface**: `http://127.0.0.1:8000`
- **Direct Agent Chat**: `http://127.0.0.1:8000/apps/self_correction_agent`
- **Discovered Applications**: `http://127.0.0.1:8000/list-apps`

In the Web UI, you can send any draft with its requirements, such as:
```text
Original Prompt/Requirements: "Write a short, engaging social media post (max 150 characters) announcing a new eco-friendly product line: 'GreenTech Gadgets'."
Initial Draft (Content to be corrected): "We have new products. They are green and techy. Buy GreenTech Gadgets now!"
```
The agent will execute its internal Chain-of-Thought inspection, invoke the character metric verification tools, and provide the refined social post.

---

## 💻 CLI Usage

### 1. Default Case (GreenTech Gadgets Launch)
```bash
uv run python main.py
```

### 2. Custom Requirements and Draft
```bash
uv run python main.py \
  -r "Write a 1-sentence professional greeting for a tech conference" \
  -d "hey guys welcome to the event"
```

### 3. Two-Stage Multi-Agent Workflow Mode
```bash
uv run python main.py -m workflow \
  -r "Write an urgent security notification about leaked tokens with 2-hour deadline"
```

### 4. Side-by-Side Comparison Mode
Compare Standalone Agent vs Multi-Agent Workflow on the same requirements:
```bash
# Option A: Using compare.py directly
uv run python compare.py

# Option B: Using main.py with --compare flag
uv run python main.py --compare
```

### 5. Running the Benchmark Suite
```bash
uv run python main.py --benchmark
```

### 6. Interactive REPL Mode
```bash
uv run python main.py --interactive
```

---

## 🧪 Running Unit Tests

Run the comprehensive pytest suite:

```bash
uv run pytest -v
```

All 14 tests validate tool accuracy, prompt templates, agent initialization, workflow execution, comparison helpers, and live ADK Web server discovery.
