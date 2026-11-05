import os
import sys
import uuid
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional
from dotenv import load_dotenv

from google.adk.workflow import Workflow, START, BaseNode
from google.adk.agents import LlmAgent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.runners import InMemoryRunner
from google.adk.tools import ToolContext, FunctionTool
from google.genai import types
import nest_asyncio

load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL_NAME", "gemini-3.5-flash")


def update_status(status: str, tool_context: ToolContext) -> str:
    """Updates the process status in session state (e.g., 'in_progress', 'completed')."""
    tool_context.state["status"] = status
    return f"Status updated to '{status}'."


def get_current_status(tool_context: ToolContext) -> str:
    """Retrieves current process status, loop iteration, and task prompt from session state."""
    status = tool_context.state.get("status", "pending")
    iteration = tool_context.state.get("loop_iteration", 0)
    task_prompt = tool_context.state.get("task_prompt", "")
    return f"status='{status}', iteration={iteration}, task_prompt='{task_prompt}'"


class ConditionChecker(BaseAgent):
    """Custom agent checking for 'completed' status in session state to stop loop."""
    name: str = "ConditionChecker"
    description: str = "Checks if process is complete and routes to continue or completed."

    async def _run_async_impl(self, context: InvocationContext) -> AsyncGenerator[Event, None]:
        status = context.session.state.get("status", "pending")
        iteration = context.session.state.get("loop_iteration", 0) + 1
        context.session.state["loop_iteration"] = iteration

        is_done = (status == "completed")

        if is_done:
            msg = f"Loop exit condition met: status is 'completed' at iteration {iteration}."
            yield Event(
                author=self.name,
                route="completed",
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=msg)],
                ),
            )
        else:
            msg = f"Condition not met: status is '{status}' at iteration {iteration}. Continuing loop."
            yield Event(
                author=self.name,
                route="continue",
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=msg)],
                ),
            )


class CompletionStep(BaseAgent):
    """Final node executed when the loop completes successfully."""
    name: str = "CompletionStep"
    description: str = "Finalizes the workflow after the loop condition is met."

    async def _run_async_impl(self, context: InvocationContext) -> AsyncGenerator[Event, None]:
        iteration = context.session.state.get("loop_iteration", 0)
        status = context.session.state.get("status", "completed")
        msg = f"Workflow completed successfully: status='{status}' after {iteration} iteration(s)."
        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=msg)],
            ),
        )


process_step = LlmAgent(
    name="ProcessingStep",
    model=GEMINI_MODEL,
    instruction="""You are a processing step inside a loop workflow.
1. Check current status with `get_current_status`.
2. Perform this iteration's task according to the overall task prompt.
3. If this iteration finishes all requirements, call `update_status` with 'completed'.
   Otherwise, call `update_status` with 'in_progress' to continue looping.
4. Summarize your progress.""",
    tools=[
        FunctionTool(update_status),
        FunctionTool(get_current_status),
    ],
)

condition_checker = ConditionChecker()
completion_step = CompletionStep()

poller = Workflow(
    name="StatusPoller",
    description="Loop workflow coordinating iterative processing and condition checking.",
    edges=[
        (START, process_step),
        (process_step, condition_checker),
        (condition_checker, {"continue": process_step, "completed": completion_step}),
    ],
)


async def run_looper(
    agent: BaseNode = poller,
    prompt: str = "Run a 2-step task: In step 1 set status to 'in_progress', in step 2 finish and set status to 'completed'.",
) -> str:
    """Executes loop workflow using InMemoryRunner and displays event stream."""
    print(f"\n=======================================================")
    print(f"  Executing [{agent.name}] | Prompt: '{prompt}'")
    print(f"=======================================================")

    runner = InMemoryRunner(agent)
    user_id = "user_looper"
    session_id = str(uuid.uuid4())

    await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
        state={"task_prompt": prompt},
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
                    print(f"\n[{event.author} -> Calling Tool: {fc.name}({fc.args})]")
                elif getattr(part, "function_response", None):
                    fr = part.function_response
                    print(f"\n[Tool Response -> {fr.name}]: {fr.response}")

        if event.actions and event.actions.escalate:
            print(f"\n>>> [Loop Terminated]: Agent '{event.author}' escalated to break loop.")

        if event.is_final_response() and event.content:
            if hasattr(event.content, "text") and event.content.text:
                final_result = event.content.text
            elif event.content.parts:
                text_parts = [p.text for p in event.content.parts if p.text]
                final_result = "".join(text_parts)

    return final_result


async def async_main():
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else (
        "Execute a 2-step process. "
        "In iteration 1, process the initial batch and set status to 'in_progress'. "
        "In iteration 2, finalize processing and set status to 'completed'."
    )
    await run_looper(prompt=prompt)


def main():
    nest_asyncio.apply()
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

