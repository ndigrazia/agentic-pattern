import asyncio
import os
import shutil
import sys
import uuid
from dotenv import load_dotenv
from google.adk.agents import Agent, LlmAgent
from google.adk.runners import InMemoryRunner
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from google.genai import types
import nest_asyncio

load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
TARGET_FOLDER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_managed_files")

# Ensure the target directory exists before the agent needs it.
os.makedirs(TARGET_FOLDER_PATH, exist_ok=True)

root_agent = LlmAgent(
    model=GEMINI_MODEL,
    name='filesystem_assistant_agent',
    instruction=('Help the user manage their files. You can list files, read files, and write files. '
                 f'You are operating in the following directory:{TARGET_FOLDER_PATH}'),
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command="npx",
                args=[
                    "-y",  # Argument for npx to auto-confirm install
                    "@modelcontextprotocol/server-filesystem",
                    # This MUST be an absolute path to a folder.
                    TARGET_FOLDER_PATH,
                ],
            ),
            # Optional: You can filter which tools from the MCP server are exposed.
            # For example, to only allow reading:
            # tool_filter=['list_directory', 'read_file']
        )
    ],
)


async def call_agent(runner: InMemoryRunner, query: str) -> str:
    """Invokes the agent with a query and returns the final response."""
    print(f"\n--- 🏃 Running Query: '{query}' ---")
    final_result = ""
    try:
        user_id = "user_123"
        session_id = str(uuid.uuid4())

        await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id=user_id,
            session_id=session_id,
        )

        msg = types.Content(
            role="user",
            parts=[types.Part.from_text(text=query)],
        )

        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=msg,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "function_call", None):
                        fc = part.function_call
                        print(f"🔧 [Tool Call -> {fc.name}]: {dict(fc.args) if fc.args else ''}")
                    elif getattr(part, "function_response", None):
                        fr = part.function_response
                        print(f"📦 [Tool Response -> {fr.name}]")

            if event.is_final_response() and event.content:
                if hasattr(event.content, "text") and event.content.text:
                    final_result = event.content.text
                elif event.content.parts:
                    text_parts = [p.text for p in event.content.parts if p.text]
                    final_result = "".join(text_parts).strip()

        print(f"✅ Agent Response:\n{final_result}")
        return final_result
    except Exception as e:
        print(f"🛑 An error occurred while processing your request: {e}")
        return f"An error occurred while processing your request: {e}"


async def main():
    """Main function to run a test on the filesystem MCP agent."""
    print("--- Google ADK MCP Filesystem Assistant Test ---")
    runner = InMemoryRunner(root_agent)

    test_query = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else "Create a file named 'test_mcp.txt' with the content 'Hello from MCP Filesystem Assistant!', and then read the content back."
    )
    await call_agent(runner, test_query)


if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())

