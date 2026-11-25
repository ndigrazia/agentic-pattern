
import asyncio
import logging
import os
from typing import Any, Dict, Optional
import uuid

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool, ToolContext
from google.adk.tools import google_search
from google.genai import types
import nest_asyncio

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RAG.Agent-GoogleSearch")

MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")

search_agent = Agent(
    name="research_assistant",
    model=MODEL_NAME,
    instruction="You help users research topics. When asked, use the Google Search tool",
    tools=[google_search]
)


async def call_agent(runner: InMemoryRunner, query: str) -> str:
    """Interacts with the Google Search RAG agent and returns the response."""
    print(f"\n==================================================")
    print(f"💬 [User Query]: '{query}'")
    print(f"==================================================")

    user_id = "user_123"
    session_id = str(uuid.uuid4())

    await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id
    )

    msg = types.Content(
        role="user",
        parts=[types.Part.from_text(text=query)]
    )

    final_result = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=msg,
    ):
        # Display search queries if grounding metadata is present
        if event.grounding_metadata and event.grounding_metadata.web_search_queries:
            for q in event.grounding_metadata.web_search_queries:
                print(f"🔍 [Google Search Query]: {q}")

        if event.is_final_response() and event.content:
            if hasattr(event.content, "text") and event.content.text:
                final_result = event.content.text
            elif event.content.parts:
                text_parts = [p.text for p in event.content.parts if p.text]
                final_result = "".join(text_parts).strip()

    print(f"\n🤖 [Agent Response]:\n{final_result}\n")
    return final_result


async def main():
    """Main function to launch the example using search_agent."""
    print("--- Launching Google ADK RAG Search Agent Example ---")
    runner = InMemoryRunner(search_agent)

    # Example query
    query = "What are the latest updates and milestones on NASA's Artemis program?"
    await call_agent(runner, query)


if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())
