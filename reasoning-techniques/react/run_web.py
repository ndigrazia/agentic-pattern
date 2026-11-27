"""Convenience launcher for Google ADK Web UI with Reasoning and Acting (ReAct) Agent."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Launch Google ADK Web UI for Reasoning and Acting (ReAct) Agent"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("ADK_PORT", "8000")),
        help="Port to bind ADK Web server (default: 8000 or $ADK_PORT)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("ADK_HOST", "127.0.0.1"),
        help="Host address to bind ADK Web server (default: 127.0.0.1)",
    )

    args = parser.parse_args()
    base_dir = Path(__file__).resolve().parent

    cmd = [
        "uv",
        "run",
        "adk",
        "web",
        str(base_dir),
        f"--host={args.host}",
        f"--port={args.port}",
    ]

    print("=" * 78)
    print("🚀 Starting Google ADK Web UI (Reasoning and Acting - ReAct Agent)")
    print(f"👉 Web Browser Interface:  http://{args.host}:{args.port}")
    print(f"👉 Direct Agent Session:    http://{args.host}:{args.port}/apps/react_agent")
    print(f"👉 Discovered App List:     http://{args.host}:{args.port}/list-apps")
    print("=" * 78)
    print("💡 In the Web UI, send multi-step queries combining knowledge retrieval,")
    print("   telemetry metrics, and mathematical calculations to see the agent")
    print("   interleave reasoning (Thought) with tool execution (Action & Observation)!")
    print("   Press Ctrl+C to terminate.")
    print("-" * 78 + "\n")

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Stopping ADK Web server...")


if __name__ == "__main__":
    main()
