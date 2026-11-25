import asyncio
import base64
import json
import sys
import warnings
from uuid import uuid4

import httpx

warnings.filterwarnings("ignore", category=DeprecationWarning)

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    Message,
    MessageSendParams,
    Part,
    Role,
    SendMessageRequest,
    Task,
    TextPart,
)


def create_test_jwt(subject: str = "test_user") -> str:
    """Generate a dummy JWT token for authentication against InsecureJWTAuthBackend."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode()).decode().rstrip("=")
    payload = base64.urlsafe_b64encode(json.dumps({"sub": subject}).encode()).decode().rstrip("=")
    return f"{header}.{payload}."


async def execute_query(
    query_text: str = "Hello! What can you help me with?",
    agent_url: str = "http://localhost:10007",
    user_id: str = "test_user",
) -> None:
    """Send a query to the A2A Agent and print the response."""
    print(f"Connecting to A2A Agent at {agent_url}...")
    headers = {"Authorization": f"Bearer {create_test_jwt(user_id)}"}

    async with httpx.AsyncClient(timeout=60, headers=headers) as http_client:
        resolver = A2ACardResolver(http_client, agent_url)
        card = await resolver.get_agent_card()
        print(f"Connected to agent: {card.name} (version: {card.version})")

        client = A2AClient(http_client, agent_card=card)

        print(f"\nUser Query: {query_text}")
        msg = Message(
            message_id=str(uuid4()),
            role=Role.user,
            parts=[Part(root=TextPart(text=query_text))],
        )
        request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(message=msg),
        )

        response = await client.send_message(request)
        result = response.root.result

        print("\nAgent Response:")
        printed_response = False
        if isinstance(result, Task):
            if result.artifacts:
                for artifact in result.artifacts:
                    for part in artifact.parts:
                        if isinstance(part.root, TextPart):
                            print(part.root.text)
                            printed_response = True
            if result.status and result.status.message:
                for part in result.status.message.parts:
                    if isinstance(part.root, TextPart):
                        print(part.root.text)
                        printed_response = True
        elif isinstance(result, Message):
            for part in result.parts:
                if isinstance(part.root, TextPart):
                    print(part.root.text)
                    printed_response = True

        if not printed_response:
            print(result.model_dump_json(indent=2, exclude_none=True))


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "Hello! What can you help me with?"
    asyncio.run(execute_query(query))


if __name__ == "__main__":
    main()

