"""Integration tests for PALM execution via InMemoryRunner."""

from __future__ import annotations

from pathlib import Path
import sys
import uuid
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.adk.runners import InMemoryRunner
from google.genai import types

from palm_agent import root_agent


@pytest.mark.asyncio
async def test_palm_code_delegation_execution():
    """Verify RootAgent delegates computational problem to CodeAgent and returns answer."""
    runner = InMemoryRunner(root_agent)
    user_id = "test_user"
    session_id = f"sess_{uuid.uuid4().hex[:6]}"

    await runner.session_service.create_session(
        app_name=runner.app_name, user_id=user_id, session_id=session_id
    )

    query = "Calculate 17 * 23 using Python and state the result."
    msg = types.Content(role="user", parts=[types.Part.from_text(text=query)])

    tool_called = False
    final_text = ""

    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=msg
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "function_call", None):
                    if part.function_call.name == "CodeAgent":
                        tool_called = True
        if event.is_final_response() and event.content:
            if hasattr(event.content, "text") and event.content.text:
                final_text = event.content.text
            elif event.content.parts:
                final_text = "".join(p.text for p in event.content.parts if p.text)

    # 17 * 23 = 391
    assert tool_called, "RootAgent should have called CodeAgent"
    assert "391" in final_text, f"Expected 391 in response, got: {final_text}"
