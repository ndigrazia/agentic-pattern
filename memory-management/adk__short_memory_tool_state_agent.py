import asyncio
import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import ToolContext
from google.genai.types import Content, Part

load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")


# 1. Create a tool which receives ToolContext as a parameter to update session state
def set_user_preference(topic: str, tool_context: ToolContext) -> dict:
    """Saves user topic preference into the session state.

    Args:
        topic: The topic preference specified by the user.
        tool_context: Automatically injected by Google ADK to access and update session state.

    Returns:
        A dictionary confirming the preference was saved.
    """
    state = tool_context.state

    # Update session-scoped and user-scoped state
    state["preferred_topic"] = topic
    state["user:preference_saved"] = True

    return {
        "status": "success",
        "message": f"Preference '{topic}' has been saved to session state.",
    }


# 2. Create an agent that calls the tool to update session state
preference_agent = LlmAgent(
    name="PreferenceAgent",
    model=GEMINI_MODEL,
    instruction=(
        "You are an assistant that records user preferences. "
        "When the user shares a preferred topic, always call the `set_user_preference` tool "
        "to save it into the session state, and then confirm to the user."
    ),
    tools=[set_user_preference],
)

# Setup Runner and Session Service
app_name = "preference_app"
user_id = "user_42"
session_id = "session_42"

session_service = InMemorySessionService()

runner = Runner(
    agent=preference_agent,
    app_name=app_name,
    session_service=session_service,
)


async def main():
    # Initialize a session with an initial state
    session = await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state={"preferred_topic": "none"},
    )
    print("=== Initial Session State ===")
    print(session.state)

    # User message that triggers the tool call
    user_prompt = "I love learning about Quantum Computing. Please save that as my preference."
    print(f"\n=== User Prompt ===\n{user_prompt}")

    user_message = Content(parts=[Part(text=user_prompt)])

    # Run the agent and stream events
    final_response_text = ""
    print("\n=== Agent Processing ===")
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=user_message,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response_text = "".join(
                    part.text for part in event.content.parts if part.text
                )

    # 3. Print the final response and updated session state
    print("\n=== Final Response ===")
    print(final_response_text.strip())

    updated_session = await session_service.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )
    print("\n=== Final Session State ===")
    print(updated_session.state)


if __name__ == "__main__":
    asyncio.run(main())
