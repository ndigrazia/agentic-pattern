"""Convenience launcher for Google ADK Web UI with Resource-Aware Optimization."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Launch Google ADK Web UI for Resource-Aware Optimization Agent"
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

    print("=" * 75)
    print("🚀 Starting Google ADK Web UI (Resource-Aware Optimization)")
    print(f"👉 Web Browser Interface:  http://{args.host}:{args.port}")
    print(f"👉 Direct Agent Session:    http://{args.host}:{args.port}/apps/optimization_agent")
    print(f"👉 Discovered App List:     http://{args.host}:{args.port}/list-apps")
    print("=" * 75)
    print("💡 In the Web UI, send short queries to see Flash, and complex architecture")
    print("   or system design queries to see Pro handle deep reasoning in real time!")
    print("   Press Ctrl+C to terminate.")
    print("-" * 75 + "\n")

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Stopping ADK Web server...")


if __name__ == "__main__":
    main()
