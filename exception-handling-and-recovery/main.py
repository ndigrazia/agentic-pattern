import asyncio
import logging
import os
import uuid
from typing import Any, Dict

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.adk.tools import ToolContext
from google.adk.workflow import START, RetryConfig, Workflow
from google.genai import types
import nest_asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ExceptionRecoveryPattern")

load_dotenv()

model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-3.8-flash")


# ============================================================================
# Domain Exceptions
# ============================================================================
class GeocodingServiceError(Exception):
    """Raised when an external geocoding service encounters an error."""
    pass


class AddressNotFoundError(Exception):
    """Raised when a specific street address cannot be found."""
    pass


# ============================================================================
# Mock Geospatial Datastores
# ============================================================================
PRECISE_DATABASE: Dict[str, Dict[str, Any]] = {
    "1600 amphitheatre pkwy, mountain view, ca": {
        "address": "1600 Amphitheatre Pkwy, Mountain View, CA 94043",
        "latitude": 37.422004,
        "longitude": -122.084409,
        "accuracy": "rooftop",
    },
    "1 infinite loop, cupertino, ca": {
        "address": "1 Infinite Loop, Cupertino, CA 95014",
        "latitude": 37.33182,
        "longitude": -122.03118,
        "accuracy": "rooftop",
    },
}

GENERAL_AREA_DATABASE: Dict[str, Dict[str, Any]] = {
    "mountain view": {
        "city": "Mountain View",
        "region": "California",
        "latitude": 37.3861,
        "longitude": -122.0839,
        "granularity": "city_centroid",
    },
    "seattle": {
        "city": "Seattle",
        "region": "Washington",
        "latitude": 47.6062,
        "longitude": -122.3321,
        "granularity": "city_centroid",
    },
}


# ============================================================================
# Tools with Exception Handling & Recovery State Tracking
# ============================================================================
def get_precise_location_info(address: str, tool_context: ToolContext) -> str:
    """Retrieves high-precision rooftop geocoding and location information."""
    cleaned = address.strip().lower()
    logger.info("Executing precise lookup for: '%s'", address)

    try:
        if "timeout" in cleaned or "service_error" in cleaned:
            raise GeocodingServiceError("Geocoding service timed out.")

        matched = next(
            (v for k, v in PRECISE_DATABASE.items() if k in cleaned or cleaned in k),
            None,
        )
        if not matched:
            raise AddressNotFoundError(f"Address '{address}' could not be resolved.")

        tool_context.state["primary_location_failed"] = False
        tool_context.state["location_result"] = {
            "resolution_level": "precise_rooftop",
            "data": matched,
        }
        tool_context.state["primary_error"] = None
        tool_context.state["fallback_used"] = False
        return f"SUCCESS: Precise coordinates found for '{address}': {matched}."

    except (AddressNotFoundError, GeocodingServiceError) as exc:
        logger.warning("Precise lookup failed: [%s] %s", exc.__class__.__name__, exc)
        tool_context.state["primary_location_failed"] = True
        tool_context.state["primary_error"] = f"[{exc.__class__.__name__}] {str(exc)}"
        tool_context.state["location_result"] = None
        tool_context.state["fallback_used"] = False
        return f"EXCEPTION: Primary lookup failed ({exc}). Fallback recovery needed."


def get_general_area_info(area_or_city: str, tool_context: ToolContext) -> str:
    """Fallback tool: Retrieves general city/regional centroid coordinates."""
    logger.info("Executing fallback lookup for area: '%s'", area_or_city)
    cleaned = area_or_city.strip().lower()

    matched = next(
        (v for k, v in GENERAL_AREA_DATABASE.items() if k in cleaned or cleaned in k),
        None,
    )
    if matched:
        tool_context.state["location_result"] = {
            "resolution_level": "city_fallback",
            "data": matched,
            "fallback_reason": tool_context.state.get("primary_error"),
        }
        tool_context.state["fallback_used"] = True
        tool_context.state["recovery_strategy"] = "city_centroid_degradation"
        return f"FALLBACK SUCCESS: Approximate city coordinates found for '{area_or_city}': {matched}."
    else:
        tool_context.state["location_result"] = None
        tool_context.state["fallback_used"] = False
        tool_context.state["recovery_strategy"] = "exhausted"
        return f"FALLBACK FAILED: General area info for '{area_or_city}' could not be found."


# ============================================================================
# Agent 1: Primary Handler
# ============================================================================
primary_handler = Agent(
    name="primary_handler",
    model=model_name,
    instruction="""
        Your job is to get precise location information.
        Use the get_precise_location_info tool with the user's provided address.
    """,
    tools=[get_precise_location_info],
    retry_config=RetryConfig(max_attempts=2, initial_delay=1.0, backoff_factor=1.5),
)

# ============================================================================
# Agent 2: Fallback Recovery Agent
# ============================================================================
fallback_handler = Agent(
    name="fallback_handler",
    model=model_name,
    instruction="""
        Check if the primary location lookup failed by looking at state:
        - Primary lookup failed: {primary_location_failed?}
        - Primary error details: {primary_error?}

        Decision rules:
        - If primary_location_failed is True:
          Extract the city/area from the user's original query and call get_general_area_info tool.
        - If primary_location_failed is False or empty:
          Do not call get_general_area_info. State that primary lookup succeeded and no fallback is needed.
    """,
    tools=[get_general_area_info],
)

# ============================================================================
# Agent 3: Final Response Formatting Agent
# ============================================================================
response_agent = Agent(
    name="response_agent",
    model=model_name,
    instruction="""
        Review the location information stored in state:
        - Location Result: {location_result?}
        - Primary Lookup Failed: {primary_location_failed?}
        - Fallback Used: {fallback_used?}

        Present this information clearly and concisely to the user.
        If fallback was used, explain that the precise lookup failed and general area coordinates were provided as fallback.
        If location_result does not exist or is empty, apologize that you could not retrieve the location.
    """,
    tools=[],  # Reasons over the final session state.
)

# ============================================================================
# Pipeline Workflow
# ============================================================================
pipeline = Workflow(
    name="robust_location_lookup_pipeline",
    edges=[
        (START, primary_handler),
        (primary_handler, fallback_handler),
        (fallback_handler, response_agent),
    ],
    description="Sequential exception handling and recovery pipeline: primary -> fallback -> response.",
)


# ============================================================================
# Execution Helper & Entry Point
# ============================================================================
async def run_location_pipeline(runner: InMemoryRunner, user_query: str) -> Dict[str, Any]:
    """Runs the workflow pipeline for a given query and prints agent outputs."""
    user_id = "demo_user"
    session_id = str(uuid.uuid4())

    await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )

    print(f"\n{'=' * 70}\n[User Query]: {user_query}\n{'=' * 70}")
    message = types.Content(role="user", parts=[types.Part.from_text(text=user_query)])

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=message,
    ):
        if event.content and event.content.parts:
            text = "".join(part.text for part in event.content.parts if part.text)
            if text:
                print(f"--- Output from agent: [{event.author}] ---")
                print(text.strip())

    session = await runner.session_service.get_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )
    print("\n--- Session State Summary ---")
    print(f"primary_location_failed: {session.state.get('primary_location_failed')}")
    print(f"fallback_used:           {session.state.get('fallback_used')}")
    print(f"recovery_strategy:       {session.state.get('recovery_strategy', 'None')}")
    print(f"location_result:         {session.state.get('location_result')}")
    return session.state


async def main():
    nest_asyncio.apply()
    runner = InMemoryRunner(pipeline)

    print("=" * 70)
    print("Google ADK Pattern: Exception Handling and Recovery Pipeline")
    print("=" * 70)

    import sys
    if len(sys.argv) > 1 and sys.argv[1] != "--all":
        custom_query = " ".join(sys.argv[1:])
        await run_location_pipeline(runner, custom_query)
        return

    # Scenario: Exception & Fallback Recovery demonstration
    print("\n>>> Demo Scenario: Precise Address Fails -> Fallback Recovery")
    await run_location_pipeline(runner, "Find location for 9999 Nonexistent Error St, Seattle, WA")

    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        print("\n>>> Scenario 1: Primary Lookup Succeeds")
        await run_location_pipeline(runner, "Find location for 1600 Amphitheatre Pkwy, Mountain View, CA")

        print("\n>>> Scenario 3: Unknown Location -> Graceful Degradation")
        await run_location_pipeline(runner, "Where is 42 Unknown Boulevard, Atlantis?")


if __name__ == "__main__":
    asyncio.run(main())
