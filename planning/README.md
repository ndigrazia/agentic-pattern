# Planning Pattern (Google ADK)

This directory implements the **Planning Pattern** using the **Google Agent Development Kit (ADK)** (`google-adk`), providing the same agent persona, behavior, and output format as the reference CrewAI implementation.

---

## Pattern Overview

The **Planning Pattern** breaks complex goals down by first establishing a structured plan before executing generation or actions. This ensures that the generated content is coherent, well-structured, and strictly adheres to requirements.

### Mapping from CrewAI to Google ADK

| CrewAI Concept | Google ADK Equivalent | Description |
| :--- | :--- | :--- |
| `ChatOpenAI(model=...)` | `os.getenv("GEMINI_MODEL_NAME")` | Gemini foundation model via `google-genai` |
| `Agent(role, goal, backstory)` | `google.adk.agents.Agent` | Agent configuration with role, goal, and backstory encoded in `instruction` |
| `Task(description, expected_output)` | `types.Content` / task prompt | Structured prompt defining the task steps and expected output structure |
| `Crew(agents, tasks, process)` | `google.adk.runners.InMemoryRunner` | Execution engine orchestrating session management and agent evaluation |
| `crew.kickoff()` | `runner.run_async(...)` | Asynchronous agent execution generating the final plan and response |

---

## File Structure

- `adk.py`: Core implementation of the Article Planner and Writer agent using Google ADK.
- `main.py`: Entrypoint delegating to `adk.py`.
- `pyproject.toml`: Project dependencies (`google-adk`, `google-genai`, `python-dotenv`, `nest-asyncio`).
- `.env`: Environment variables (`GEMINI_MODEL_NAME`, `GOOGLE_API_KEY`).

---

## How to Run

Run with `uv`:

```bash
cd ~/python/pattern/planning
uv run python adk.py
```

or via `main.py`:

```bash
uv run python main.py
```

