"""Agent definition for Google ADK Web integration."""

from __future__ import annotations

import os
from pathlib import Path
import sys

# Ensure package directory is in sys.path
package_dir = str(Path(__file__).resolve().parent)
parent_dir = str(Path(__file__).resolve().parent.parent)
for p in (package_dir, parent_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

from dotenv import load_dotenv

try:
    from .router_agent import QueryRouterAgent, create_flash_agent, create_pro_agent
except ImportError:
    from router_agent import QueryRouterAgent, create_flash_agent, create_pro_agent

load_dotenv()

flash_agent = create_flash_agent()
pro_agent = create_pro_agent()

# Root agent discovered and served by ADK Web
root_agent = QueryRouterAgent(
    name="optimization_agent",
    description=(
        "Resource-Aware Optimization Agent. Dynamically assesses query complexity "
        "and routes to Flash or Pro models to minimize costs and latency."
    ),
    complexity_threshold=0.5,
    flash_agent=flash_agent,
    pro_agent=pro_agent,
    sub_agents=[flash_agent, pro_agent],
)

