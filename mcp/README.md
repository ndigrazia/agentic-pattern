# Model Context Protocol (MCP) Pattern (Google ADK)

This directory demonstrates integrating the **Model Context Protocol (MCP)** with the **Google Agent Development Kit (ADK)** (`google-adk`). It covers both standard MCP transport architectures:

1. **Stdio Transport:** Connecting to local MCP servers running as child processes (e.g., `@modelcontextprotocol/server-filesystem` via `npx`).
2. **Streamable HTTP Transport:** Connecting to HTTP-based MCP servers (e.g., Python `FastMCP` microservices).

---

## Pattern Overview

The **Model Context Protocol (MCP)** provides an open standard for LLMs and AI agents to securely discover and invoke tools, inspect resources, and interact with external systems.

Google ADK supports MCP integration through `McpToolset` (and `MCPToolset`), converting MCP server tools into native ADK tools that `Agent` and `LlmAgent` can dynamically call during reasoning loops.

### Key ADK MCP Components

| Component | Class | Description |
| :--- | :--- | :--- |
| **MCP Toolset** | `google.adk.tools.mcp_tool.McpToolset` | Converts MCP tools into ADK agent tools |
| **Stdio Transport** | `StdioServerParameters` / `StdioConnectionParams` | Runs a local process via stdio (`npx`, `python`, etc.) |
| **HTTP Transport** | `StreamableHTTPConnectionParams` | Connects to remote or local HTTP MCP servers |
| **SSE Transport** | `SseConnectionParams` | Connects to Server-Sent Events MCP endpoints |
| **Runner** | `google.adk.runners.InMemoryRunner` | Orchestrates agent sessions and streaming events |

---

## Directory Structure

```
pattern/mcp/
├── .env                              # Environment variables (GOOGLE_API_KEY, GEMINI_MODEL_NAME)
├── pyproject.toml                    # Dependencies (google-adk, fastmcp, etc.)
├── README.md                         # Documentation
├── agent.py                          # Filesystem Agent (Stdio Transport via npx)
├── mcp_managed_files/                # Sandboxed directory managed by the Filesystem Agent
└── fastmcp_client_adk_agent/         # FastMCP HTTP Service & ADK Client Agent
    ├── .env                          # Local agent environment variables
    ├── fastmcp_server.py             # FastMCP HTTP Server (exposes 'greet' tool on port 9000)
    ├── agent.py                      # ADK Greeter Agent (HTTP connection to FastMCP)
    └── main.py                       # Test execution script using InMemoryRunner
```

---

## Setup & Prerequisites

### 1. Requirements
- Python `>= 3.12`
- Node.js & `npx` (for `@modelcontextprotocol/server-filesystem`)
- `uv` package manager

### 2. Environment Variables
Create or verify `.env` in `pattern/mcp/` or the project root:
```env
GOOGLE_API_KEY="your-google-api-key"
GEMINI_MODEL_NAME="gemini-2.5-flash"
FASTMCP_SERVER_URL="http://127.0.0.1:9000/mcp"
```

### 3. Install Dependencies
```bash
uv sync
```


---

## How to Run

### Example 1: Filesystem Assistant Agent (Stdio Transport)

The `filesystem_assistant_agent` interacts with files inside `mcp_managed_files/` using the official `@modelcontextprotocol/server-filesystem`.

#### Run the Agent Test Script:
```bash
uv run python pattern/mcp/agent.py
```

#### Run with a Custom File Operation Query:
```bash
uv run python pattern/mcp/agent.py "Create a file named notes.txt with 'Meeting at 3 PM', then list the directory."
```

---

### Example 2: FastMCP Greeter Agent (Streamable HTTP Transport)

This example demonstrates connecting an ADK agent to a separate FastMCP tool server over HTTP.

#### Step 1: Start the FastMCP Server
```bash
uv run python pattern/mcp/fastmcp_client_adk_agent/fastmcp_server.py
```
*The server will start on `http://127.0.0.1:9000/mcp`.*

#### Step 2: Run the ADK Client Agent
```bash
# Run from repository root
uv run pattern/mcp/fastmcp_client_adk_agent/main.py "Please greet Alice"

# Or from within the agent directory
cd pattern/mcp/fastmcp_client_adk_agent
uv run main.py "Please greet Bob"
```

---

### Example 3: Interactive Web UI (`adk web`)

Google ADK provides a built-in browser UI for testing agents interactively.

#### Launch Web UI for the FastMCP Agent:
```bash
uv run adk web pattern/mcp/fastmcp_client_adk_agent
```
Or use the alias:
```bash
uv run adk web pattern/mcp/fastmcp_client_agent
```

#### Launch Web UI for all MCP Agents:
```bash
uv run adk web pattern/mcp
```

Open `http://127.0.0.1:8000` in your browser to chat interactively with your agent and observe real-time tool calls.

---

### Example 4: Interactive Terminal Chat (`adk run`)

```bash
uv run adk run pattern/mcp/fastmcp_client_adk_agent
```

---

## Code Reference

### Stdio Transport (`pattern/mcp/agent.py`)
```python
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioServerParameters

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="filesystem_assistant_agent",
    instruction=f"Help the user manage their files in: {TARGET_FOLDER_PATH}",
    tools=[
        McpToolset(
            connection_params=StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem", TARGET_FOLDER_PATH],
            )
        )
    ],
)
```

### HTTP Transport (`pattern/mcp/fastmcp_client_adk_agent/agent.py`)
```python
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="fastmcp_greeter_agent",
    instruction='You are a friendly assistant. Greet users with the "greet" tool.',
    tools=[
        McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url="http://127.0.0.1:9000/mcp"
            ),
            tool_filter=["greet"],
        )
    ],
)
```

