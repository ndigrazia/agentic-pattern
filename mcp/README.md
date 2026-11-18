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

