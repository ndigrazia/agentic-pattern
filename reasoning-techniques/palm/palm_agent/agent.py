"""Program-Aided Language Models (PALM / PAL) Agent implementation for Google ADK."""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Any, Optional

# Ensure package directory is in sys.path
package_dir = str(Path(__file__).resolve().parent)
parent_dir = str(Path(__file__).resolve().parent.parent)
for p in (package_dir, parent_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.code_executors import BaseCodeExecutor, BuiltInCodeExecutor
from google.adk.tools import agent_tool, google_search

try:
    from .prompts import (
        CODE_AGENT_INSTRUCTION,
        PALM_ROOT_INSTRUCTION,
        SEARCH_AGENT_INSTRUCTION,
    )
except ImportError:
    from prompts import (
        CODE_AGENT_INSTRUCTION,
        PALM_ROOT_INSTRUCTION,
        SEARCH_AGENT_INSTRUCTION,
    )

load_dotenv()


def _patch_adk_agent() -> None:
    """Enhances Agent.__init__ to gracefully support:

    1. code_executor passed as class or list (e.g. [BuiltInCodeExecutor] or BuiltInCodeExecutor).
    2. Fallback model mapping if gemini-2.0-flash is requested but deprecated by the API.
    3. Inheriting description from instruction if description is not explicitly provided.
    """
    orig_init = getattr(Agent, "_palm_orig_init", None)
    if orig_init is not None:
        return

    _orig_init = Agent.__init__

    def _adk_agent_init(self: Any, *args: Any, **kwargs: Any) -> None:
        # 1. Normalize code_executor
        if "code_executor" in kwargs:
            ce = kwargs["code_executor"]
            if isinstance(ce, (list, tuple)) and len(ce) > 0:
                ce = ce[0]
            if isinstance(ce, type) and issubclass(ce, BaseCodeExecutor):
                ce = ce()
            kwargs["code_executor"] = ce

        # 2. Map model if deprecated gemini-2.0-flash is passed
        model = kwargs.get("model")
        active_model = os.getenv("GEMINI_MODEL_NAME", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
        if model == "gemini-2.0-flash" and active_model != "gemini-2.0-flash":
            kwargs["model"] = active_model
        elif not model:
            kwargs["model"] = active_model

        # 3. Ensure description exists for AgentTool discovery
        desc = kwargs.get("description")
        inst = kwargs.get("instruction")
        name = kwargs.get("name", "Agent")
        if not desc and inst:
            first_line = inst.strip().split("\n")[0].strip()
            kwargs["description"] = first_line or f"Specialist agent: {name}"

        _orig_init(self, *args, **kwargs)

    Agent._palm_orig_init = _orig_init
    Agent.__init__ = _adk_agent_init


# Apply patch to support [BuiltInCodeExecutor] and API model compatibility
_patch_adk_agent()


def get_default_model() -> str:
    """Retrieves default Gemini model name from environment or fallback."""
    return os.getenv("GEMINI_MODEL_NAME", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))


# ---------------------------------------------------------------------------
# Program-Aided Language Models (PALM) Multi-Agent Architecture
# ---------------------------------------------------------------------------

# 1. Search Specialist Agent
search_agent = Agent(
    model="gemini-2.0-flash",
    name="SearchAgent",
    description="You're a specialist in Google Search",
    instruction="""
You're a specialist in Google Search
""",
    tools=[google_search],
)

# 2. Code Execution Specialist Agent
coding_agent = Agent(
    model="gemini-2.0-flash",
    name="CodeAgent",
    description="You're a specialist in Code Execution",
    instruction="""
You're a specialist in Code Execution
""",
    code_executor=[BuiltInCodeExecutor],
)

# 3. Root Agent orchestrating PALM reasoning
root_agent = Agent(
    name="RootAgent",
    model="gemini-2.0-flash",
    description="Root Agent",
    instruction=PALM_ROOT_INSTRUCTION,
    tools=[
        agent_tool.AgentTool(agent=search_agent),
        agent_tool.AgentTool(agent=coding_agent),
    ],
)


def create_palm_system(
    model_name: Optional[str] = None,
    root_instruction: Optional[str] = None,
) -> Agent:
    """Factory function to build a configurable PALM agent system.

    Args:
        model_name: Optional model override (e.g. gemini-2.5-flash).
        root_instruction: Optional custom root instruction.

    Returns:
        Configured RootAgent.
    """
    model = model_name or get_default_model()

    search = Agent(
        model=model,
        name="SearchAgent",
        description="You're a specialist in Google Search",
        instruction=SEARCH_AGENT_INSTRUCTION,
        tools=[google_search],
    )

    code = Agent(
        model=model,
        name="CodeAgent",
        description="You're a specialist in Code Execution",
        instruction=CODE_AGENT_INSTRUCTION,
        code_executor=[BuiltInCodeExecutor],
    )

    return Agent(
        name="RootAgent",
        model=model,
        description="Root Agent",
        instruction=root_instruction or PALM_ROOT_INSTRUCTION,
        tools=[
            agent_tool.AgentTool(agent=search),
            agent_tool.AgentTool(agent=code),
        ],
    )
