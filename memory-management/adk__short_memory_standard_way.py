import asyncio
import os
import time
from dotenv import load_dotenv
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.sessions import InMemorySessionService
from google.adk.tools.tool_context import ToolContext

load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")


def log_user_login(tool_context: ToolContext) -> dict:
    """Updates the session state upon a user login event.

    This tool encapsulates all state changes related to a user login.
    Args:
        tool_context: Automatically provided by ADK, gives access to session state.
    Returns:
        A dictionary confirming the action was successful.
    """
    # Access the state directly through the provided context.
    state = tool_context.state

    # Get current values or defaults, then update the state.
    # This is much cleaner and co-locates the logic.
    login_count = state.get("user:login_count", 0) + 1

    state["user:login_count"] = login_count
    state["task_status"] = "active"
    state["user:last_login_ts"] = time.time()
    state["temp:validation_needed"] = True

    print("State updated from within the `log_user_login` tool.")

    return {
        "status": "success",
        "message": f"User login tracked. Total logins: {login_count}.",
    }


# 1. Setup
session_service = InMemorySessionService()

app_name, user_id, session_id = "state_app_tool", "user3", "session3"


async def main():
    session = await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state={"user:login_count": 0, "task_status": "idle"},
    )

    print(f"Initial state: {session.state}")

    # We create a ToolContext manually for this standalone example.
    mock_context = ToolContext(
        invocation_context=InvocationContext(
            invocation_id="standalone_inv",
            session=session,
            session_service=session_service,
        )
    )

    log_user_login(mock_context)

    # Commit the state delta recorded by the tool to the session service
    await session_service.append_event(
        session=session,
        event=Event(actions=mock_context._event_actions),
    )

    updated_session = await session_service.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )

    print(f"\nState after agent run: {updated_session.state}")


if __name__ == "__main__":
    asyncio.run(main())
