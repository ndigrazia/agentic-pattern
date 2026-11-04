import os
import uuid
import asyncio
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types
import nest_asyncio

# Load environment variables from .env file for security
load_dotenv()

# 1. Explicitly define the language model for clarity
model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-3.8-flash")

# 2. Define a clear and focused agent using Google ADK
# Translating CrewAI role, goal, and backstory into ADK Agent instructions
ROLE = "Article Planner and Writer"
GOAL = "Plan and then write a concise, engaging summary on a specified topic."
BACKSTORY = (
    "You are an expert technical writer and content strategist. "
    "Your strength lies in creating a clear, actionable plan before writing, "
    "ensuring the final summary is both informative and easy to digest."
)

INSTRUCTION = f"""You are an {ROLE}.

Goal:
{GOAL}

Backstory:
{BACKSTORY}

When assigned a topic:
1. Create a bullet-point plan for a summary on the specified topic.
2. Write the summary based on your plan, keeping it around 200 words.

Expected Output Format:
A final report containing two distinct sections:

### Plan
- A bulleted list outlining the main points of the summary.

### Summary
- A concise and well-structured summary of the topic.
"""

planner_writer_agent = Agent(
    name="ArticlePlannerAndWriter",
    model=model_name,
    description=GOAL,
    instruction=INSTRUCTION,
)

# 3. Define the execution function equivalent to Crew kickoff
async def kickoff_task(agent: Agent, topic: str) -> str:
    """
    Executes the planning and writing task using the ADK InMemoryRunner,
    mirroring the CrewAI kickoff execution flow.
    """
    runner = InMemoryRunner(agent)
    user_id = "user_123"
    session_id = str(uuid.uuid4())

    await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id
    )

    task_description = (
        f"1. Create a bullet-point plan for a summary on the topic: '{topic}'.\n"
        f"2. Write the summary based on your plan, keeping it around 200 words."
    )

    msg = types.Content(
        role="user",
        parts=[types.Part.from_text(text=task_description)]
    )

    final_result = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=msg,
    ):
        if event.is_final_response() and event.content:
            if hasattr(event.content, "text") and event.content.text:
                final_result = event.content.text
            elif event.content.parts:
                text_parts = [part.text for part in event.content.parts if part.text]
                final_result = "".join(text_parts)

    return final_result


async def main():
    # 4. Define topic and run task with identical behavior as CrewAI
    topic = "The importance of Reinforcement Learning in AI"
    print("## Running the planning and writing task ##")
    result = await kickoff_task(planner_writer_agent, topic)
    print("\n\n---\n## Task Result ##\n---")
    print(result)


if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())
