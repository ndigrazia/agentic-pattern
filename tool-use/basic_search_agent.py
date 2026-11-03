import uuid
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool, google_search
from google.genai import types
from google.adk.events import Event
import nest_asyncio

load_dotenv()

# Define variables required for Session setup and Agent execution
APP_NAME = "Google Search_agent"
GEMINI_MODEL = os.getenv("GEMINI_MODEL_NAME", "gemini-3.5-flash")

# Define Agent with access to search tool
root_agent = Agent(
    name="basic_search_agent",
    model=GEMINI_MODEL,
    description="Agent to answer questions using Google Search.",
    instruction="I can answer your questions by searching the internet. Just ask me anything!",
    tools=[google_search]  # Google Search is a pre-built tool to perform Google searches.
)

# Agent Interaction
async def call_agent(runner: InMemoryRunner, query: str):
    """Function to call the agent with a query and return the response."""    
    final_result = ""
    try:
        user_id = "user_123"
        session_id = str(uuid.uuid4())
        
        await runner.session_service.create_session(
            app_name=runner.app_name, user_id=user_id,
            session_id=session_id
        )
        
        for event in runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=types.Content(
                role='user',
                parts=[types.Part(text=query)]
             ),  
        ):
            if event.is_final_response() and event.content:
                # Try to get text directly from event.content
                # to avoid iterating parts
                if hasattr(event.content, 'text') and event.content.text:
                    final_result = event.content.text
                elif event.content.parts:
                    # Fallback: Iterate through parts and extract text (might trigger warning)
                    text_parts = [part.text for part in event.content.parts if part.text]
                    final_result = "".join(text_parts)
                break
        return final_result
    except Exception as e:
        print(f"An error occurred while processing your request: {e}")
        return f"An error occurred while processing your request: {e}"    
    
async def main():
    """Main function to run the ADK example."""
    print("--- Google ADK Tool Use Example ---")
    runner = InMemoryRunner(root_agent, app_name=APP_NAME)
    # Example Usage
    query = "What is the capital of France?"
    response = await call_agent(runner, query)
    print(f"Agent Response: {response}")

if __name__ == "__main__":
    import asyncio
    nest_asyncio.apply()
    asyncio.run(main())
