import asyncio
import os
import sys
from uuid import uuid4

import httpx
from dotenv import load_dotenv

load_dotenv()


async def test_a2a_communication(
    prompt: str = "Calculate 25 multiplied by 14. Use the math agent.",
    host: str = "http://localhost:8000",
) -> None:
    """Test A2A communication between coordinator_agent and math_agent via ADK."""
    print("=" * 60)
    print("Testing A2A Communication via ADK Web Server")
    print(f"Target: {host}")
    print(f"Prompt: {prompt}")
    print("=" * 60)

    user_id = f"user_{uuid4().hex[:6]}"
    session_id = f"session_{uuid4().hex[:6]}"

    async with httpx.AsyncClient(timeout=60) as client:
        # 1. Verify A2A agent card
        card_url = f"{host}/a2a/math_agent/.well-known/agent-card.json"
        print(f"\n1. Checking Math Agent A2A Card at {card_url}...")
        card_resp = await client.get(card_url)
        if card_resp.status_code == 200:
            print(f"   ✅ Agent Card verified: {card_resp.json().get('name')}")
        else:
            print(f"   ⚠️ Warning: Status {card_resp.status_code}: {card_resp.text}")

        # 2. Create session on coordinator_agent
        print(f"\n2. Creating session on coordinator_agent ({session_id})...")
        sess_url = f"{host}/apps/coordinator_agent/users/{user_id}/sessions/{session_id}"
        sess_resp = await client.post(sess_url)
        print(f"   Session response: {sess_resp.status_code}")

        # 3. Send message to coordinator_agent
        print("\n3. Sending message to coordinator_agent...")
        run_payload = {
            "appName": "coordinator_agent",
            "userId": user_id,
            "sessionId": session_id,
            "newMessage": {
                "role": "user",
                "parts": [{"text": prompt}],
            },
        }

        run_resp = await client.post(f"{host}/run", json=run_payload)
        print(f"   Run response: {run_resp.status_code}")

        if run_resp.status_code == 200:
            events = run_resp.json()
            print("\n4. Execution Events Trace:")
            for event in events:
                author = event.get("author", "unknown")
                content = event.get("content", {})
                parts = content.get("parts", [])
                for part in parts:
                    if "text" in part:
                        print(f"   [{author}]: {part['text']}")
        else:
            print(f"   ❌ Error: {run_resp.text}")


def main():
    prompt = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Calculate 25 multiplied by 14. Use the math agent."
    )
    asyncio.run(test_a2a_communication(prompt))


if __name__ == "__main__":
    main()
