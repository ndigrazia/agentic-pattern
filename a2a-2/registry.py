import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import httpx
from google.adk.agents.remote_a2a_agent import (
    AGENT_CARD_WELL_KNOWN_PATH,
    RemoteA2aAgent,
)

logger = logging.getLogger("a2a_registry")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent / "registry.json"


class A2AAgentRegistry:
    """Registry for discovering, storing, and managing A2A agents."""

    def __init__(self, registry_file: Optional[Union[str, Path]] = None):
        self.registry_file = Path(registry_file or DEFAULT_REGISTRY_PATH)
        self._agents: Dict[str, Dict[str, Any]] = {}
        self.load()

    def load(self) -> None:
        """Load registered agents from backing JSON file."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    self._agents = json.load(f)
            except Exception as e:
                logger.warning("Failed to load registry: %s", e)
                self._agents = {}
        else:
            self._agents = {}

    def save(self) -> None:
        """Save registered agents to backing JSON file."""
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(self._agents, f, indent=2)

    def register(
        self,
        name: Optional[str] = None,
        card_data: Optional[Dict[str, Any]] = None,
        file_path: Optional[Union[str, Path]] = None,
        url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Register an A2A agent from file, URL, or dict."""
        data: Dict[str, Any] = {}
        if file_path:
            p = Path(file_path).resolve()
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        elif url:
            base_url = url.rstrip("/")
            target_url = base_url if base_url.endswith(".json") else f"{base_url}{AGENT_CARD_WELL_KNOWN_PATH}"
            with httpx.Client(timeout=10) as client:
                resp = client.get(target_url)
                if resp.status_code != 200:
                    resp = client.get(f"{base_url}/.well-known/agent.json")
                resp.raise_for_status()
                data = resp.json()
        elif card_data:
            data = card_data
        else:
            raise ValueError("Must provide file_path, url, or card_data.")

        agent_name = name or data.get("name")
        if not agent_name:
            raise ValueError("Agent card must contain a 'name' field.")

        entry = {
            "name": agent_name,
            "description": data.get("description", ""),
            "url": data.get("url", url or ""),
            "version": data.get("version", "1.0.0"),
            "skills": data.get("skills", []),
            "capabilities": data.get("capabilities", {}),
            "card": data,
        }
        self._agents[agent_name] = entry
        self.save()
        logger.info("Registered agent: '%s' (%s)", agent_name, entry["url"])
        return entry

    def unregister(self, name: str) -> bool:
        """Remove an agent from the registry."""
        if name in self._agents:
            del self._agents[name]
            self.save()
            return True
        return False

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieve agent entry by name."""
        return self._agents.get(name)

    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents."""
        return list(self._agents.values())

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search agents by name, description, or skill tags."""
        q = query.lower()
        results = []
        for entry in self._agents.values():
            if q in entry.get("name", "").lower() or q in entry.get("description", "").lower():
                results.append(entry)
                continue
            for skill in entry.get("skills", []):
                tags = [t.lower() for t in skill.get("tags", [])]
                if q in skill.get("name", "").lower() or q in tags or q in skill.get("id", "").lower():
                    results.append(entry)
                    break
        return results

    def create_remote_agent(self, name: str, **kwargs: Any) -> RemoteA2aAgent:
        """Create an ADK RemoteA2aAgent from the registered agent."""
        entry = self.get(name)
        if not entry:
            raise KeyError(f"Agent '{name}' is not registered.")
        card_url = entry.get("url", "")
        if not card_url.endswith(".json"):
            card_url = f"{card_url.rstrip('/')}{AGENT_CARD_WELL_KNOWN_PATH}"
        return RemoteA2aAgent(
            name=entry["name"],
            description=entry.get("description", ""),
            agent_card=card_url,
            **kwargs,
        )



def main():
    parser = argparse.ArgumentParser(description="A2A Agent Registry CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("list", help="List all registered A2A agents")

    reg_parser = subparsers.add_parser("register", help="Register an A2A agent")
    reg_parser.add_argument("--name", help="Optional custom name for the agent")
    reg_parser.add_argument("--file", help="Path to local agent.json file")
    reg_parser.add_argument("--url", help="URL of live A2A agent endpoint")

    unreg_parser = subparsers.add_parser("unregister", help="Unregister an agent by name")
    unreg_parser.add_argument("name", help="Name of the agent to remove")

    search_parser = subparsers.add_parser("search", help="Search agents by keyword or skill tag")
    search_parser.add_argument("query", help="Keyword or skill tag to search for")

    args = parser.parse_args()
    registry = A2AAgentRegistry()

    if args.command == "list":
        agents = registry.list_agents()
        print(f"\n📦 Registered A2A Agents ({len(agents)}):")
        print("=" * 60)
        for a in agents:
            skills = [s.get("id", "") for s in a.get("skills", [])]
            print(f"• Name:        {a['name']}")
            print(f"  Description: {a['description']}")
            print(f"  URL:         {a['url']}")
            print(f"  Skills:      {', '.join(skills) if skills else 'None'}")
            print("-" * 60)

    elif args.command == "register":
        if not args.file and not args.url:
            print("Error: Must provide either --file or --url", file=sys.stderr)
            sys.exit(1)
        entry = registry.register(name=args.name, file_path=args.file, url=args.url)
        print(f"✅ Successfully registered agent '{entry['name']}' ({entry['url']})")

    elif args.command == "unregister":
        if registry.unregister(args.name):
            print(f"✅ Successfully unregistered agent '{args.name}'")
        else:
            print(f"❌ Agent '{args.name}' not found", file=sys.stderr)
            sys.exit(1)

    elif args.command == "search":
        matches = registry.search(args.query)
        print(f"\n🔍 Found {len(matches)} matching agent(s) for '{args.query}':")
        print("=" * 60)
        for a in matches:
            print(f"• {a['name']}: {a['description']} (URL: {a['url']})")
            for s in a.get("skills", []):
                print(f"    - Skill: {s.get('name')} (tags: {s.get('tags', [])})")
            print("-" * 60)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
