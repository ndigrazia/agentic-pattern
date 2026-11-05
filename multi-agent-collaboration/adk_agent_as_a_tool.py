import asyncio
import os
import sys
import uuid
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools import agent_tool
from google.adk.runners import InMemoryRunner
from google.genai import types

load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")

# 1. A simple function tool for the core capability.
# This follows the best practice of separating actions from reasoning.
def generate_image(prompt: str) -> dict:
    """
    Generates an image based on a textual prompt.
    Args:
    prompt: A detailed description of the image to generate.
    Returns:
    A dictionary with the status and the generated image bytes.
    """
    print(f"\n[TOOL]: Generating image for prompt: '{prompt}'")
    # In a real implementation, this would call an image generation API.
    # For this example, we return mock image data.
    mock_image_bytes = b"mock_image_data_for_a_cat_wearing_a_hat"
    return {
        "status": "success",
        # The tool returns the raw bytes, the agent will handle the Part creation.
        "image_bytes": mock_image_bytes,
        "mime_type": "image/png",
    }


# 2. Refactor the ImageGeneratorAgent into an LlmAgent.
# It now correctly uses the input passed to it.
image_generator_agent = LlmAgent(
    name="ImageGen",
    model=GEMINI_MODEL,
    description="Generates an image based on a detailed text prompt. The input should be a descriptive prompt of the desired image.",
    instruction=(
        "You are an image generation specialist. Your task is to take the user's request "
        "and use the `generate_image` tool to create the image. "
        "The user's entire request should be used as the 'prompt' "
        "argument for the tool. "
        "After the tool returns the image bytes, summarize the outcome."
    ),
    tools=[generate_image],
)

# 3. Wrap the corrected agent in an AgentTool.
# The tool automatically inherits its name and description from the wrapped agent.
image_tool = agent_tool.AgentTool(
    agent=image_generator_agent,
)

# 4. The parent agent remains unchanged. Its logic was correct.
artist_agent = LlmAgent(
    name="Artist",
    model=GEMINI_MODEL,
    description="A creative artist agent that invents prompts and calls the ImageGen tool.",
    instruction=(
        "You are a creative artist. First, invent a creative and descriptive prompt for an image based on the user's request. "
        "Then, use the `ImageGen` tool to generate the image using your prompt. "
        "Finally, present the artistic concept and describe the created artwork."
    ),
    tools=[image_tool],
)


async def main():
    user_request = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else "Create an image of a cat wearing a bowler hat sipping tea in a vintage Victorian café."
    )

    print("=" * 65)
    print("Running Agent-As-A-Tool Pattern")
    print(f"Parent Agent: [{artist_agent.name}]")
    print(f"Wrapped Sub-Agent Tool: [{image_generator_agent.name}]")
    print(f"User Request: {user_request}")
    print("=" * 65)

    runner = InMemoryRunner(artist_agent)
    user_id = "user_123"
    session_id = str(uuid.uuid4())

    await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )

    msg = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_request)],
    )

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=msg,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"\n[{event.author}]:\n{part.text.strip()}")
                elif getattr(part, "function_call", None):
                    fc = part.function_call
                    print(f"\n[{event.author} -> Calling Tool '{fc.name}']:\nArgs: {dict(fc.args)}")
                elif getattr(part, "function_response", None):
                    fr = part.function_response
                    print(f"\n[Tool Response -> '{fr.name}']:\n{dict(fr.response)}")

    print("\n" + "=" * 65)
    print("Execution Completed Successfully")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
