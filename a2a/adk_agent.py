import datetime
import os

from google.adk.agents import LlmAgent
from google.adk.models import Gemini
from google.adk.tools.google_api_tool import CalendarToolset


def create_agent(client_id, client_secret) -> LlmAgent:
    """Constructs the ADK agent."""
    model_name = os.getenv('GEMINI_MODEL_NAME', os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-001'))
    toolset = CalendarToolset(client_id=client_id, client_secret=client_secret)
    return LlmAgent(
        model=Gemini(model=model_name),
        name='calendar_agent',
        description="An agent that can help manage a user's calendar",
        instruction=f"""
            You are an agent that can help manage a user's calendar.

            Users will request information about the state of their calendar or to make changes to
            their calendar. Use the provided tools for interacting with the calendar API.

            If not specified, assume the calendar the user wants is the 'primary' calendar.

            When using the Calendar API tools, use well-formed RFC3339 timestamps.

            Today is {datetime.datetime.now()}.
        """,
        tools=[toolset],
    )
