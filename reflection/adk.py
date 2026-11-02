import uuid
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from google.adk.agents import Agent, LlmAgent
from google.adk.workflow import Workflow, START, JoinNode
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool, google_search
from google.genai import types
from google.adk.events import Event
import nest_asyncio

load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL_NAME", "gemini-3.5-flash")


# The first agent generates the initial draft.
generator = LlmAgent(
    name="DraftWriter",
    model=GEMINI_MODEL,
    description="Generates initial draft content on a given subject.",
    instruction="Write a short, informative paragraph about the user's subject.",
    output_key="draft_text" # The output is saved to this state key.
)

# The second agent critiques the draft from the first agent.
reviewer = LlmAgent(
    name="FactChecker",
    model=GEMINI_MODEL,
    description="Reviews a given text for factual accuracy and provides a structured critique.",
    instruction="""
        You are a meticulous fact-checker.
        1. Read the text provided in the state key 'draft_text':
        {draft_text}
        2. Carefully verify the factual accuracy of all claims.
        3. Your final output must be a dictionary containing two keys:
            - "status": A string, either "ACCURATE" or "INACCURATE".
            - "reasoning": A string providing a clear explanation for your status, citing specific issues if any are found.
    """,
    output_key="review_result" # The output is saved to this state key. 
)

# The Workflow orchestrates the execution of the generator and reviewer agents in sequence.
review_pipeline = Workflow(
    name="WriteAndReview_Pipeline",
    edges=[
        (START, generator),
        (generator, reviewer),
    ],
    description="Coordinates the draft generation and fact-checking review process."
)
root_agent = review_pipeline


# --- Execution Logic ---

async def run_pipeline(runner: InMemoryRunner, prompt: str = "The Apollo 11 moon landing"):
    """Runs the draft generation and review reflection pipeline to execute all agents."""
    print(f"\n--- Running Write and Review Pipeline: '{prompt}' ---")
    final_result = ""
    try:
        user_id = "user_123"
        session_id = str(uuid.uuid4())

        await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id=user_id,
            session_id=session_id
        )

        msg = types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)]
        )

        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=msg,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"\n[{event.author}]:\n{part.text}")
            if event.is_final_response() and event.content:
                if hasattr(event.content, "text") and event.content.text:
                    final_result = event.content.text
                elif event.content.parts:
                    text_parts = [part.text for part in event.content.parts if part.text]
                    final_result = "".join(text_parts)

        session = await runner.session_service.get_session(
            app_name=runner.app_name,
            user_id=user_id,
            session_id=session_id
        )
        print("\n--- Stored Session State Across All Agents ---")
        for k, v in session.state.items():
            print(f"[{k}]:\n{v}\n")

        print("\n--- Final Pipeline Output ---")
        print(final_result)
        return final_result
    except Exception as e:
        print(f"An error occurred while running the pipeline: {e}")
        return f"An error occurred while running the pipeline: {e}"


async def main():
    """Main function to run the ADK reflection pattern example."""
    print("--- Google ADK Reflection Pattern Example ---")
    runner = InMemoryRunner(root_agent)
    await run_pipeline(runner, "The Apollo 11 moon landing")


if __name__ == "__main__":
    import asyncio
    nest_asyncio.apply()
    asyncio.run(main())

