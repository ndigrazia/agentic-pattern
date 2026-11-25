import os
import subprocess
import sys
from pathlib import Path


def main():
    port = os.getenv("ADK_PORT", "8000")
    base_dir = Path(__file__).resolve().parent

    cmd = [
        "uv",
        "run",
        "adk",
        "web",
        "--a2a",
        f"--port={port}",
        str(base_dir),
    ]

    print("=" * 70)
    print("🚀 Starting ADK Web Server with A2A Protocol Support")
    print(f"👉 Web UI available at: http://localhost:{port}")
    print(f"👉 A2A Math Agent Card at: http://localhost:{port}/a2a/math_agent/.well-known/agent-card.json")
    print("=" * 70)

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nStopping ADK Web server...")


if __name__ == "__main__":
    main()
