import asyncio
import os
import uuid
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.workflow import Workflow, START
from google.adk.runners import InMemoryRunner
from google.genai import types

# Load environment variables (such as GOOGLE_API_KEY and GEMINI_MODEL_NAME)

load_dotenv()

model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")

# This agent's output will be saved to session.state["data"]
step1 = Agent(
    name="Step1_Fetch",
    model=model_name,
    output_key="data",
    instruction="Fetch key details and informative facts about the user's query.",
)

# This agent will use the data from the previous step.
# We instruct it on how to find and use this data.
step2 = Agent(
    name="Step2_Process",
    model=model_name,
    instruction="Analyze the information found in state['data'] and provide a summary.",
)

pipeline = Workflow(
    name="MyPipeline",
    edges=[
        (START, step1),
        (step1, step2),
    ],
    description="A sequential pipeline workflow executing step1 followed by step2.",
)

# When the pipeline is run with an initial input, Step1 will execute,
# its response will be stored in session.state["data"], and then
# Step2 will execute, using the information from the state as
# instructed.


async def main():
    print("=" * 60)
    print("Running ADK Workflow Pipeline")
    print("=" * 60)

    # Initialize runner with the sequential workflow
    runner = InMemoryRunner(pipeline)
    user_id = "user_123"
    session_id = str(uuid.uuid4())

    # Create session
    await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )

    query = "Fetch details about the James Webb Space Telescope."
    print(f"\n[User Query]: {query}\n")

    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=query)],
    )

    # Run the pipeline and stream events
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=message,
    ):
        if event.content and event.content.parts:
            text = "".join(part.text for part in event.content.parts if part.text)
            if text:
                print(f"--- Output from agent: [{event.author}] ---")
                print(text.strip())
                print()

    # Inspect the session state to verify data was saved
    session = await runner.session_service.get_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )
    print("=" * 60)
    print("Session State Verification:")
    print(f"session.state['data'] present: {'data' in session.state}")
    print(f"Length of data in state: {len(session.state.get('data', ''))} characters")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())


