import os
import uuid
import asyncio
import subprocess
from dotenv import load_dotenv
import nest_asyncio

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from google.genai import types
from google.auth.credentials import Credentials
from google.auth.transport.requests import Request
from google.cloud import discoveryengine_v1 as discoveryengine
from google.api_core.client_options import ClientOptions
import google.auth

# Load local environment configuration
load_dotenv()

# Configuration variables
APP_NAME = "vsearch_app"
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "tma-gemini-enterprise")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
DATA_STORE_ID = os.getenv("DATA_STORE_ID", "my-search-datastore")
GEMINI_MODEL = os.getenv("GEMINI_MODEL_NAME", "gemini-3.5-flash")


class GCloudCredentials(Credentials):
    """Fallback credentials provider utilizing gcloud CLI access token."""

    def __init__(self):
        super().__init__()
        self.token = self._fetch_token()

    def _fetch_token(self) -> str:
        return subprocess.check_output(
            ["gcloud", "auth", "print-access-token"], text=True
        ).strip()

    def refresh(self, request):
        self.token = self._fetch_token()


def get_search_client() -> discoveryengine.SearchServiceClient:
    """Initializes and returns a Discovery Engine SearchServiceClient."""
    client_options = ClientOptions(quota_project_id=PROJECT_ID)
    if LOCATION != "global":
        client_options.api_endpoint = f"{LOCATION}-discoveryengine.googleapis.com"

    # Attempt to load Application Default Credentials; fall back to gcloud token if needed
    try:
        creds, _ = google.auth.default()
        creds.refresh(Request())
    except Exception:
        creds = GCloudCredentials()

    return discoveryengine.SearchServiceClient(
        credentials=creds, client_options=client_options
    )


# Initialize Search Client
search_client = get_search_client()


def search_datastore(query: str) -> str:
    """Searches the enterprise Vertex AI Search datastore for internal AI documentation,
    concepts, architecture specifications, and guides.

    Args:
        query: The search query or terms to look up in the knowledge base.

    Returns:
        A formatted string containing relevant excerpts, titles, and document sources.
    """
    print(f"\n🔍 [Tool Call: search_datastore] Querying: '{query}'")
    serving_config = (
        f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection"
        f"/dataStores/{DATA_STORE_ID}/servingConfigs/default_search"
    )

    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=query,
        content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
            snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                return_snippet=True
            )
        ),
        page_size=3,
    )

    try:
        response = search_client.search(request)
        results = []
        for item in response.results:
            doc = item.document
            derived = dict(doc.derived_struct_data) if doc.derived_struct_data else {}
            title = derived.get("title", doc.id or "Document")
            link = derived.get("link", "")
            snippets = derived.get("snippets", [])
            snippet_texts = [
                s.get("snippet", "")
                for s in snippets
                if isinstance(s, dict) or hasattr(s, "get")
            ]
            clean_snippet = " ".join(filter(None, snippet_texts))

            results.append(
                f"Document Title: {title}\n"
                f"Source URI: {link}\n"
                f"Content Excerpt: {clean_snippet}"
            )

        if not results:
            return "No matching documents or passages found in the knowledge base."

        return "\n\n---\n\n".join(results)

    except Exception as e:
        return f"Error executing search query against datastore: {e}"


# Define the ADK Tool
search_tool = FunctionTool(search_datastore)

# Define the Root Agent
root_agent = Agent(
    name="vsearch_agent",
    model=GEMINI_MODEL,
    description=(
        "Enterprise search assistant powered by Google ADK with access to "
        "the Vertex AI Search datastore (my-search-datastore)."
    ),
    instruction="""You are an enterprise AI technical assistant.
You have access to the company's internal AI knowledge base via the `search_datastore` tool.
When users ask questions about AI architectures, RAG, LLMs, agents, or technical guidelines:
1. Always call the `search_datastore` tool with relevant keywords to retrieve grounded context.
2. Formulate your answer based strictly on the retrieved knowledge base excerpts.
3. Clearly cite the document source (title and source URI) at the end of your answer.
4. If the retrieved context does not contain the answer, state that clearly instead of speculating.
""",
    tools=[search_tool],
)


# Agent Interaction Helper
async def call_agent(runner: InMemoryRunner, query: str) -> str:
    """Interacts with the agent for a given user query and prints streaming events."""
    print(f"\n==================================================")
    print(f"💬 [User Query]: '{query}'")
    print(f"==================================================")
    final_result = ""

    try:
        user_id = "user_enterprise_1"
        session_id = str(uuid.uuid4())

        await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id=user_id,
            session_id=session_id,
        )

        message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=query)],
        )

        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=message,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "function_call", None):
                        print(f"⚙️  [Agent Decided to Call Tool]: {part.function_call.name}")
                    if getattr(part, "function_response", None):
                        print(f"📥 [Received Tool Response for]: {part.function_response.name}")

            if event.is_final_response() and event.content:
                if hasattr(event.content, "text") and event.content.text:
                    final_result = event.content.text
                elif event.content.parts:
                    text_parts = [p.text for p in event.content.parts if p.text]
                    final_result = "".join(text_parts).strip()

        print(f"\n🤖 [Agent Final Answer]:\n{final_result}")
        return final_result

    except Exception as e:
        error_msg = f"Error during agent execution: {e}"
        print(f"🛑 {error_msg}")
        return error_msg


async def main():
    """Main execution entrypoint for testing the Vertex AI Search ADK Agent."""
    print("🚀 Initializing Google ADK Agent with Vertex AI Search (my-search-datastore)...")
    runner = InMemoryRunner(root_agent, app_name=APP_NAME)

    # Test Query: RAG Chunking Strategies
    await call_agent(
        runner,
        "What chunking strategies are described for Retrieval-Augmented Generation (RAG)?",
    )


if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())

