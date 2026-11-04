import asyncio
import nest_asyncio
from adk import main as run_collaboration


def main():
    nest_asyncio.apply()
    run_collaboration()


if __name__ == "__main__":
    main()
