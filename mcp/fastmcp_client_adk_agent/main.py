import asyncio
import os
import sys
import uuid
from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from google.genai import types
import nest_asyncio

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
load_dotenv()

from agent import root_agent

async def call_agent(runner: InMemoryRunner, query: str) -> str:
    """Interacts with the agent using InMemoryRunner."""
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
    """Main execution function to test the agent."""
    print("=== Google ADK Agent Test ===")
    runner = InMemoryRunner(root_agent)

    query = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else "Please greet David"
    )
    await call_agent(runner, query)


if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())
