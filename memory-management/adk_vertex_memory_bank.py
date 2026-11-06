import asyncio
import os
import uuid
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.events import Event
from google.adk.memory import InMemoryMemoryService, VertexAiMemoryBankService
from google.adk.memory.memory_entry import MemoryEntry
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, VertexAiSessionService
from google.adk.tools import ToolContext
from google.genai.types import Content, Part

load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("PROJECT_ID", "your-gcp-project")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
AGENT_ENGINE_ID = os.getenv("AGENT_ENGINE_ID")


# 1. Tool that updates Vertex AI Memory Bank
async def save_to_memory_bank(
    fact: str,
    tool_context: ToolContext,
) -> dict:
    """Saves user information or facts to Vertex AI Memory Bank."""
    entry = MemoryEntry(content=Content(parts=[Part(text=fact)]))
    try:
        await tool_context.add_memory(memories=[entry])
    except NotImplementedError:
        event = Event(content=Content(parts=[Part(text=fact)]))
        await tool_context.add_events_to_memory(events=[event])

    print(f" [Tool Call: save_to_memory_bank] Stored: '{fact}'")
    return {
        "status": "success",
        "message": f"Successfully stored in Vertex AI Memory Bank: '{fact}'.",
    }


async def recall_from_memory_bank(
    query: str,
    tool_context: ToolContext,
) -> dict:
    """Searches and retrieves relevant memories from Vertex AI Memory Bank."""
    search_response = await tool_context.search_memory(query=query)
    found = [
        "".join(part.text for part in m.content.parts if part.text)
        for m in search_response.memories
        if m.content and m.content.parts
    ]
    print(f" [Tool Call: recall_from_memory_bank] Found {len(found)} items for '{query}'")
    return {
        "status": "success",
        "retrieved_memories": found,
    }


# 2. Agent configured with Memory Bank tools
memory_agent = LlmAgent(
    name="VertexMemoryBankAgent",
    model=GEMINI_MODEL,
    instruction=(
        "You are an assistant connected to Vertex AI Memory Bank for long-term memory. "
        "When the user asks you to remember information, invoke `save_to_memory_bank`. "
        "When the user asks about previously saved facts, invoke `recall_from_memory_bank`."
    ),
    tools=[save_to_memory_bank, recall_from_memory_bank],
)

# 3. Initialize VertexAiMemoryBankService
app_name = "vertex-memory-app"
user_id = "user-enterprise"

if AGENT_ENGINE_ID and PROJECT_ID:
    print(f"Using VertexAiMemoryBankService (Agent Engine: {AGENT_ENGINE_ID})...")
    memory_service = VertexAiMemoryBankService(
        project=PROJECT_ID,
        location=LOCATION,
        agent_engine_id=AGENT_ENGINE_ID,
    )
    session_service = VertexAiSessionService(
        project=PROJECT_ID,
        location=LOCATION,
        agent_engine_id=AGENT_ENGINE_ID,
    )
else:
    print("NOTE: AGENT_ENGINE_ID not set; using local fallback.")
    memory_service = InMemoryMemoryService()
    session_service = InMemorySessionService()

runner = Runner(
    agent=memory_agent,
    app_name=app_name,
    session_service=session_service,
    memory_service=memory_service,
)


# 4. Main Execution
async def main():
    # Session 1: Store memory via agent tool
    session_1_id = f"session-vertex-{uuid.uuid4().hex[:8]}"
    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_1_id,
    )

    user_prompt_1 = "Please remember: I have mongoDB cluster in us-central1 with 3 replicas."
    print("\n==================================================================")
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

    print(f"\n[Session 1] Agent Response:\n{response_1_text.strip()}\n")

    # Direct search on Memory Bank Service
    print("==================================================================")
    print("Direct inspection of Memory Bank Service:")
    search_result = await memory_service.search_memory(
        app_name=app_name,
        user_id=user_id,
        query="database mongoDB region us-central1",
    )
    for i, mem in enumerate(search_result.memories, 1):
        mem_text = "".join(p.text for p in mem.content.parts if p.text)
        print(f"  Memory #{i}: {mem_text}")

    # Session 2: Cross-Session Recall in a new session
    session_2_id = f"session-vertex-{uuid.uuid4().hex[:8]}"
    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_2_id,
    )

    user_prompt_2 = "What database configuration did I save earlier?"
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

    print(f"\n[Session 2] Agent Response:\n{response_2_text.strip()}\n")
    print("==================================================================")


if __name__ == "__main__":
    asyncio.run(main())

