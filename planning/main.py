import asyncio
import nest_asyncio
from adk import main as run_planning_agent


def main():
    nest_asyncio.apply()
    asyncio.run(run_planning_agent())


if __name__ == "__main__":
    main()

