import os
import asyncio
from dotenv import load_dotenv
import nest_asyncio

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool as langchain_tool
from langchain.agents import create_agent

load_dotenv()

# Initialize the Language Model using Gemini
model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-3.8-flash")
api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

try:
    llm = ChatGoogleGenerativeAI(model=model_name, api_key=api_key, temperature=0)
    print(f"Language model initialized: {llm.model}")
except Exception as e:
    print(f"Error initializing language model: {e}")
    llm = None
    
# --- Define a Tool ---
@langchain_tool
def search_information(query: str) -> str:
    """
    Provides factual information on a given topic. Use this tool to
    find answers to phrases like 'capital of France' or 'weather in London?'.
    """
    print(f"\n--- 🛠️ Tool Called: search_information with query: '{query}' ---")

    # Simulate a search tool with a dictionary of predefined results.
    simulated_results = {
        "weather in london": "The weather in London is currently cloudy with a temperature of 15°C.",
        "capital of france": "The capital of France is Paris.",
        "population of earth": "The estimated population of Earth is around 8 billion people.",
        "tallest mountain": "Mount Everest is the tallest mountain above sea level.",
        "default": f"Simulated search result for '{query}': No specific information found, but the topic seems interesting."
    }
    
    result = simulated_results.get(query.lower(), simulated_results["default"])
    
    print(f"--- TOOL RESULT: {result} ---")

    return result

tools = [search_information]

# --- Create a Tool-Calling Agent ---
if llm:
    # In LangChain 1.x, create_agent creates a compiled agent graph with tool-calling capabilities.
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt="""You are a helpful assistant. Use available tools to answer factual questions. 
        No invent information use ONLY the tools provided.""",
    )
else:
    agent = None

async def run_agent_with_tool(query: str):
    """Invokes the agent with a query and prints the final response."""
    print(f"\n--- 🏃 Running Agent with Query: '{query}' ---")
    if not agent:
        print("🛑 Agent not initialized.")
        return
    try:
        response = await agent.ainvoke({"messages": [{"role": "user", "content": query}]})
        final_message = response["messages"][-1]
        if isinstance(final_message.content, list):
            output = "".join(part.get("text", "") for part in final_message.content if isinstance(part, dict))
        else:
            output = str(final_message.content)
        print("\n--- ✅ Final Agent Response ---")
        print(output)
    except Exception as e:
        print(f"\n🛑 An error occurred during agent execution: {e}")

async def main():
    """Runs all agent queries concurrently."""
    tasks = [
        run_agent_with_tool("What is the capital of France?"),
        run_agent_with_tool("What's the weather like in London?"),
        run_agent_with_tool("Tell me something about dogs.") # Should trigger the default tool response
    ]
    
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    #nest_asyncio.apply() # Only needed if running in a Jupyter notebook or similar environment
    asyncio.run(main())




