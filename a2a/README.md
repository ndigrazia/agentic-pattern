# Agent-to-Agent (A2A) Pattern with Google ADK

This pattern demonstrates how to create an **Agent-to-Agent (A2A)** server utilizing Google's Agent Development Kit (ADK) and the A2A protocol. It exposes an ADK-based Calendar Agent as an interoperable A2A server with OAuth2 authentication and Starlette/Uvicorn hosting.

## Architecture

```
┌──────────────────┐               ┌─────────────────────────────────────┐
│    A2A Client    │ ─── JSON-RPC ──▶ │         A2A Starlette Server        │
│ (HTTP / OAuth2)  │ ◀── SSE Stream ─ │       (localhost:10007)             │
└──────────────────┘               └──────────────────┬──────────────────┘
                                                      │
                                           ┌──────────▼──────────┐
                                           │  ADK Agent Executor │
                                           └──────────┬──────────┘
                                                      │
                                           ┌──────────▼──────────┐
                                           │ Calendar ADK Agent  │
                                           │  (CalendarToolset)  │
                                           └─────────────────────┘
```

## Features

- **Agent-to-Agent (A2A) Protocol**: Implements standard A2A specification with JSON-RPC over HTTP and streaming capabilities.
- **AgentCard Discovery**: Exposes `/.well-known/agent.json` declaring agent capabilities, skills, and security schemes.
- **Google ADK Integration**: Wraps Google ADK Runner, Sessions, and Toolsets into an `ADKAgentExecutor`.
- **OAuth2 Flow Support**: Supports OAuth2 authorization for calendar operations with redirect callbacks at `/authenticate`.

## Prerequisites

- Python 3.12+
- `uv` package manager
- Gemini API Key / Google Cloud credentials in `.env`:
  ```bash
  GOOGLE_API_KEY=your_api_key
  GOOGLE_CLIENT_ID=your_client_id       # Optional, for OAuth calendar tools
  GOOGLE_CLIENT_SECRET=your_client_sec # Optional, for OAuth calendar tools
  ```

## Running the Server

From the repository root:
```bash
uv run __main__.py
```

Or from inside `pattern/a2a`:
```bash
uv run __main__.py --host localhost --port 10007
```

## Testing and Executing Queries

1. Fetch the Agent Card:
   ```bash
   curl http://localhost:10007/.well-known/agent.json
   ```

2. Execute a query with the client:
   ```bash
   # Default query
   uv run python pattern/a2a/example.py

   # Custom query
   uv run python pattern/a2a/example.py "What are your core capabilities?"
   ```


