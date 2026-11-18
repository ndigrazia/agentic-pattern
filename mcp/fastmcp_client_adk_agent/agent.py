import asyncio
import os
import shutil
import sys
import uuid
from dotenv import load_dotenv
from google.adk.agents import Agent, LlmAgent
from google.adk.runners import InMemoryRunner
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams
from google.genai import types

load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")

# Define the FastMCP server's address.
# FastMCP http transport defaults to the /mcp endpoint.
FASTMCP_SERVER_URL = os.getenv("FASTMCP_SERVER_URL", "http://127.0.0.1:9000/mcp")

# Alias for backwards compatibility if referenced
HttpServerParameters = StreamableHTTPConnectionParams

root_agent = LlmAgent(
    model=GEMINI_MODEL,
    name='fastmcp_greeter_agent',
    instruction="""
    You are a friendly assistant that can greet people by their name. Use the "greet" tool.""",
    tools=[
        MCPToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=FASTMCP_SERVER_URL
            ),
            # Optional: Filter which tools from the MCP server are exposed
            # For this example, we're expecting only 'greet'
            tool_filter=['greet']
        )
    ],
)
