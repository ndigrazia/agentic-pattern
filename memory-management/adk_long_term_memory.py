import asyncio
import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.events import Event
from google.adk.memory import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import ToolContext
from google.genai.types import Content, Part

load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")


# 1. Tool to update Long-Term Memory (InMemoryMemoryService)
async def save_to_long_term_memory(
    fact: str,
    tool_context: ToolContext,
) -> dict:
    """Saves a piece of information or fact into long-term memory.

    Args:
        fact: The factual information or preference to store in long-term memory.
        tool_context: Injected by Google ADK to access the memory service.

    Returns:
        A dictionary confirming the memory has been saved.
    """
    event = Event(content=Content(parts=[Part(text=fact)]))
    await tool_context.add_events_to_memory(events=[event])

    print(f" [Tool Call: save_to_long_term_memory] Saved fact: '{fact}'")
    return {
        "status": "success",
        "message": f"Successfully saved to long-term memory: '{fact}'.",
    }


# Helper tool to recall from Long-Term Memory
async def recall_from_long_term_memory(
    query: str,
    tool_context: ToolContext,
) -> dict:
    """Searches and retrieves relevant facts from long-term memory.

    Args:
        query: The keywords to search in long-term memory.
        tool_context: Injected by Google ADK to access the memory service.

    Returns:
        A dictionary containing matching memories found.
    """
    response = await tool_context.search_memory(query=query)
    found = [
        "".join(part.text for part in m.content.parts if part.text)
        for m in response.memories
        if m.content and m.content.parts
    ]
    print(f" [Tool Call: recall_from_long_term_memory] Found for '{query}': {found}")
    return {
        "status": "success",
        "memories": found,
    }


# 2. Create Agent configured with tools
memory_agent = LlmAgent(
    name="LongTermMemoryAgent",
    model=GEMINI_MODEL,
    instruction=(
        "You are an assistant equipped with long-term memory. "
        "When the user asks you to remember or store information, invoke `save_to_long_term_memory`. "
        "When the user asks about previously stored information, invoke `recall_from_long_term_memory`."
    ),
    tools=[save_to_long_term_memory, recall_from_long_term_memory],
)

# Setup InMemoryMemoryService and InMemorySessionService
app_name = "adk_memory_app"
user_id = "user_alpha"

session_service = InMemorySessionService()
memory_service = InMemoryMemoryService()  # Long-Term Memory Store

runner = Runner(
    agent=memory_agent,
    app_name=app_name,
    session_service=session_service,
    memory_service=memory_service,
)


# 3. Main execution to demonstrate saving and cross-session retrieval
async def main():
    # Session 1: Ask the agent to save information to Long-Term Memory
    session_1_id = "session_001"
    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_1_id,
    )

    user_prompt_1 = "Please remember this into long-term memory: My favorite programming language is Python and I specialize in distributed AI systems."
    print("==================================================================")
    print(f"[Session 1] User Prompt:\n{user_prompt_1}\n")

    message_1 = Content(parts=[Part(text=user_prompt_1)])

    response_1_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_1_id,
        new_message=message_1,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            response_1_text = "".join(p.text for p in event.content.parts if p.text)

    print(f"\n[Session 1] Final Agent Response:\n{response_1_text.strip()}\n")

    # Direct inspection of InMemoryMemoryService
    print("==================================================================")
    print("Direct inspection of InMemoryMemoryService (Long-Term Storage):")
    search_result = await memory_service.search_memory(
        app_name=app_name,
        user_id=user_id,
        query="programming language distributed AI",
    )
    for i, mem in enumerate(search_result.memories, 1):
        mem_text = "".join(p.text for p in mem.content.parts if p.text)
        print(f"  Memory #{i} (ID: {mem.id}): {mem_text}")

    # Session 2: New independent session recalling the saved memory
    session_2_id = "session_002"
    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_2_id,
    )

    user_prompt_2 = "What programming language and specialization did I mention earlier?"
    print("\n==================================================================")
    print(f"[Session 2 - New Session] User Prompt:\n{user_prompt_2}\n")

    message_2 = Content(parts=[Part(text=user_prompt_2)])

    response_2_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_2_id,
        new_message=message_2,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            response_2_text = "".join(p.text for p in event.content.parts if p.text)

    print(f"\n[Session 2] Final Agent Response:\n{response_2_text.strip()}\n")
    print("==================================================================")


if __name__ == "__main__":
    asyncio.run(main())
