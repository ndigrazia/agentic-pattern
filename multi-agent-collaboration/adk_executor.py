import os
import sys
import uuid
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional
from dotenv import load_dotenv
from google.adk.agents import InvocationContext, LlmAgent, BaseAgent
from google.adk.workflow import Workflow, START, JoinNode
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool, google_search
from google.genai import types
from google.adk.events import Event
import nest_asyncio

load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL_NAME", "gemini-3.5-flash")


# Correctly implement a custom agent by extending BaseAgent
class TaskExecutor(BaseAgent):
    """A specialized agent with custom, non-LLM behavior."""
    name: str = "TaskExecutor"
    description: str = "Executes a predefined computational or deterministic task."

    async def _run_async_impl(self, context: InvocationContext) -> AsyncGenerator[Event, None]:
        """Custom implementation logic for the task."""
        # Simulated deterministic data processing logic
        analysis_data = (
            "System metrics analysis completed:\n"
            "- 4 services healthy\n"
            "- Latency p95: 42ms\n"
            "- Error rate: 0.01%\n"
            "- Anomaly detection: No critical issues found."
        )

        # Store output in session state for collaborating agents to access
        context.session.state["system_metrics"] = analysis_data

        # Yield a valid ADK Event with a types.Content object
        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=f"Task completed successfully:\n{analysis_data}")]
            )
        )

task_executor = TaskExecutor()

# Define individual agents with proper initialization
greeter = LlmAgent(
    name="Greeter",
    model=GEMINI_MODEL,
    instruction=(
        "You are a friendly greeter. Greet the user warmly, introduce your team "
        "(Greeter and TaskExecutor), and offer assistance."
    ),
    description="A friendly agent dedicated to greeting users.",
)


# Create a parent agent and assign its sub-agents
coordinator = LlmAgent(
    name="Coordinator",
    model=GEMINI_MODEL,
    description="A coordinator that can greet users and execute tasks.",
    instruction=(
        "You are the coordinator orchestrating specialized sub-agents.\n"
        "- When asked to greet, delegate to the 'Greeter'.\n"
        "- When asked to perform a task or check system metrics, delegate to the 'TaskExecutor'.\n"
        "- When asked to do both, coordinate by delegating to Greeter first, then to TaskExecutor.\n"
    ),
    sub_agents=[
        greeter,
        task_executor,
    ],
)

# Workflow pipeline for sequential execution of both agents
collaboration_workflow = Workflow(
    name="MultiAgentWorkflow",
    edges=[
        (START, greeter),
        (greeter, task_executor),
    ],
    description="Sequential collaboration workflow executing Greeter followed by TaskExecutor.",
)

root_agent = coordinator


async def run_agent(agent: BaseAgent, prompt: str = "Hello!") -> str:
    """Executes any given agent or workflow using InMemoryRunner."""
    print(f"\n=======================================================")
    print(f"  Executing [{agent.name}] | Prompt: '{prompt}'")
    print(f"=======================================================")

    runner = InMemoryRunner(agent)
    user_id = "user_123"
    session_id = str(uuid.uuid4())

    await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )

    msg = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])

    final_result = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=msg,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"\n[{event.author}]:\n{part.text}")
                elif getattr(part, "function_call", None):
                    fc = part.function_call
                    target = (
                        fc.args.get("agent_name", "sub-agent")
                        if hasattr(fc, "args")
                        else "sub-agent"
                    )
                    print(f"\n[{event.author} -> Delegating to {target}]")

        if event.is_final_response() and event.content:
            if hasattr(event.content, "text") and event.content.text:
                final_result = event.content.text
            elif event.content.parts:
                text_parts = [p.text for p in event.content.parts if p.text]
                final_result = "".join(text_parts)

    return final_result


async def run_greeter(prompt: str = "Say hello and introduce the team.") -> str:
    """Executes only the Greeter agent."""
    return await run_agent(greeter, prompt)


async def run_task_executor(prompt: str = "Run metrics analysis.") -> str:
    """Executes only the TaskExecutor agent."""
    return await run_agent(task_executor, prompt)


async def run_coordinator(
    prompt: str = "Please greet the user and after that, execute a system metrics analysis task."
) -> str:
    """Executes both agents collaboratively via Coordinator delegation."""
    return await run_agent(coordinator, prompt)


async def run_workflow(prompt: str = "Greet and run task.") -> str:
    """Executes both agents sequentially through a Workflow pipeline."""
    return await run_agent(collaboration_workflow, prompt)


# Backward-compatible helper matching original signature
async def run_collaboration(
    runner: InMemoryRunner = None, prompt: str = "Say hello!"
) -> str:
    """Runs collaboration using coordinator."""
    return await run_coordinator(prompt)


async def async_main():
    """Runs a specific agent or the full suite based on CLI arguments."""
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else "all"

    if arg in ("greeter", "greet"):
        await run_greeter("Hello! Please introduce yourself and the team.")
    elif arg in ("task", "task_executor", "executor"):
        await run_task_executor("Execute system metrics task.")
    elif arg in ("workflow", "pipe"):
        await run_workflow("Run sequential pipeline.")
    elif arg in ("coordinator", "coord"):
        await run_coordinator(
            "Please greet the user and after that, execute a system metrics analysis task."
        )
    else:
        # Default 'all': Demonstrates executing both agents individually, then collaboratively
        print(">>> DEMO 1: Execute Greeter Agent Individually")
        await run_greeter("Hello! Introduce yourself and the team.")

        print("\n>>> DEMO 2: Execute TaskExecutor Agent Individually")
        await run_task_executor("Run metrics analysis.")

        print("\n>>> DEMO 3: Execute Both Agents Collaboratively via Coordinator")
        await run_coordinator(
            "Please greet the user and after that, execute a system metrics analysis task."
        )


def main():
    nest_asyncio.apply()
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

