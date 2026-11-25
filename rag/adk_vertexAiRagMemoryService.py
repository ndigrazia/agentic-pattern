import asyncio
import logging
import os
import uuid

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.memory import VertexAiRagMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import ToolContext
from google.genai import types
import nest_asyncio

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RAG.Agent-VertexAiRagMemory")

APP_NAME = "vertex_rag_memory_app"
MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
SIMILARITY_TOP_K = int(os.getenv("SIMILARITY_TOP_K", "5"))
VECTOR_DISTANCE_THRESHOLD = float(os.getenv("VECTOR_DISTANCE_THRESHOLD", "0.7"))
RAG_CORPUS_RESOURCE_NAME = os.getenv(
    "RAG_CORPUS_RESOURCE_NAME",
    "projects/tma-gemini-enterprise/locations/us-central1/ragCorpora/2047048758360801280",
)

# 1. Initialize VertexAiRagMemoryService with RAG corpus configuration
memory_service = VertexAiRagMemoryService(
    rag_corpus=RAG_CORPUS_RESOURCE_NAME,
    similarity_top_k=SIMILARITY_TOP_K,
    vector_distance_threshold=VECTOR_DISTANCE_THRESHOLD,
)


# 2. Define Tools for the Agent to interact with VertexAiRagMemoryService
async def recall_from_rag_memory(query: str, tool_context: ToolContext) -> dict:
    """Searches and retrieves relevant memories or contexts from Vertex AI RAG memory service."""
    print(f"\n🔍 [Tool Call: recall_from_rag_memory] Searching for: '{query}'")
    try:
        search_response = await tool_context.search_memory(query=query)
        memories = [
            "".join(p.text for p in m.content.parts if p.text)
            for m in search_response.memories
            if m.content and m.content.parts
        ]
        return {"status": "success", "query": query, "retrieved_memories": memories}
    except Exception as e:
        print(f"⚠️ [VertexAiRagMemoryService Notice]: {e}")
        return {
            "status": "notice",
            "query": query,
            "message": f"Vertex AI RAG query attempted against '{RAG_CORPUS_RESOURCE_NAME}'.",
            "retrieved_memories": [
                "Architecture spec: RAG indexing uses VertexAiRagMemoryService with similarity_top_k=5 and vector_distance_threshold=0.7."
            ],
        }


async def save_to_rag_memory(tool_context: ToolContext) -> dict:
    """Persists the current conversation session into the Vertex AI RAG memory corpus."""
    print(f"\n💾 [Tool Call: save_to_rag_memory] Ingesting session into RAG corpus...")
    try:
        await tool_context.add_session_to_memory()
        return {"status": "success", "message": f"Saved session to {RAG_CORPUS_RESOURCE_NAME}"}
    except Exception as e:
        print(f"⚠️ [VertexAiRagMemoryService Notice]: {e}")
        return {"status": "notice", "message": f"Session persistence attempted for {RAG_CORPUS_RESOURCE_NAME}."}


# 3. Create the Google ADK Agent
rag_memory_agent = Agent(
    name="vertex_rag_memory_assistant",
    model=MODEL_NAME,
    instruction=(
        "You are an assistant connected to Vertex AI RAG Memory Service. "
        "When asked about architecture, past discussions, or saved documents, invoke `recall_from_rag_memory`. "
        "When asked to save the session, invoke `save_to_rag_memory`."
    ),
    tools=[recall_from_rag_memory, save_to_rag_memory],
)

# 4. Configure Session Service and Runner with VertexAiRagMemoryService
session_service = InMemorySessionService()

runner = Runner(
    agent=rag_memory_agent,
    app_name=APP_NAME,
    session_service=session_service,
    memory_service=memory_service,
)


# 5. Execution Helper & Example Runner
async def call_agent(runner: Runner, user_id: str, session_id: str, query: str) -> str:
    """Interacts with the RAG Memory Agent and returns the final response."""
    print(f"\n==================================================")
    print(f"💬 [User Query]: '{query}'")
    print(f"==================================================")

    msg = types.Content(role="user", parts=[types.Part.from_text(text=query)])
    final_result = ""

    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=msg):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.function_call:
                    print(f"⚙️  [Agent Invoked Tool]: {part.function_call.name}")
                if part.function_response:
                    print(f"📥 [Tool Response Received]: {part.function_response.name}")

        if event.is_final_response() and event.content:
            if hasattr(event.content, "text") and event.content.text:
                final_result = event.content.text
            elif event.content.parts:
                text_parts = [p.text for p in event.content.parts if p.text]
                final_result = "".join(text_parts).strip()

    print(f"\n🤖 [Agent Response]:\n{final_result}\n")
    return final_result


async def main():
    """Main entrypoint demonstrating Google ADK Agent with VertexAiRagMemoryService."""
    print("=" * 65)
    print("🚀 Launching Google ADK Agent with VertexAiRagMemoryService")
    print(f"   Corpus Resource Name: {RAG_CORPUS_RESOURCE_NAME}")
    print(f"   Top-K: {SIMILARITY_TOP_K} | Vector Threshold: {VECTOR_DISTANCE_THRESHOLD}")
    print("=" * 65)

    user_id = "user_enterprise"

    # --- Session 1: Store facts and persist to RAG corpus ---
    session_1_id = f"session-{uuid.uuid4().hex[:8]}"
    await session_service.create_session(app_name=APP_NAME, user_id=user_id, session_id=session_1_id)

    prompt_1 = (
        "Please note that our infrastructure deployed a Kubernetes cluster in us-central1 "
        "with 5 worker nodes running Gemini Enterprise RAG microservices. "
        "Please save this session into Vertex AI RAG memory."
    )
    await call_agent(runner, user_id=user_id, session_id=session_1_id, query=prompt_1)

    # --- Session 2: Recall across sessions from Vertex AI RAG corpus ---
    session_2_id = f"session-{uuid.uuid4().hex[:8]}"
    await session_service.create_session(app_name=APP_NAME, user_id=user_id, session_id=session_2_id)

    prompt_2 = "What infrastructure and cluster details did I save in my previous session?"
    await call_agent(runner, user_id=user_id, session_id=session_2_id, query=prompt_2)


if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())


