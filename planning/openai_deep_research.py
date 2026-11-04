import os
import sys
from dotenv import load_dotenv
from openai import OpenAI, AuthenticationError

# Load environment variables from .env if present
load_dotenv()

api_key = os.environ.get("OPENAI_API_KEY")

system_instructions = """
You are an expert market analyst. Prepare a detailed, data-backed report.
Include specific market figures, vendor comparisons, and trends.
Support claims with inline citations and return all source metadata.
"""

user_query = "Analyze the state of global solid-state battery commercialization in 2025-2026."

def run_deep_research():
    if not api_key or api_key == "your-api-key":
        print("Error: OPENAI_API_KEY environment variable is not set.", file=sys.stderr)
        print("Please set your OpenAI API key before running:", file=sys.stderr)
        print("  export OPENAI_API_KEY=\"sk-...\"", file=sys.stderr)
        print("or add it to your .env file.", file=sys.stderr)
        sys.exit(1)

    # Initialize the OpenAI client
    client = OpenAI(api_key=api_key)

    print(f"Submitting Deep Research query: {user_query}")
    print("Waiting for response from o3-deep-research (this may take several minutes)...")

    try:
        # Make the Deep Research API call via client.responses
        response = client.responses.create(
            model="o3-deep-research",
            input=[
                {
                    "role": "developer",
                    "content": [{"type": "input_text", "text": system_instructions}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_query}],
                },
            ],
            reasoning={
                "summary": "auto"  # 'auto' or 'detailed'
            },
            tools=[
                {"type": "web_search_preview"},
                {
                    "type": "code_interpreter",
                    "container": {"type": "auto", "file_ids": []},
                },
            ],
        )
    except AuthenticationError as e:
        print(f"Authentication failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"API call failed: {e}", file=sys.stderr)
        sys.exit(1)

    # 1. Access final synthesized report
    report_text = response.output[-1].content[0].text
    print("\n=== FINAL REPORT ===\n")
    print(report_text)

    # 2. Extract citations and references
    annotations = getattr(response.output[-1].content[0], "annotations", [])
    if annotations:
        print("\n=== CITATIONS & SOURCES ===\n")
        for i, citation in enumerate(annotations, 1):
            title = getattr(citation, "title", "No Title")
            url = getattr(citation, "url", "No URL")
            start = getattr(citation, "start_index", "?")
            end = getattr(citation, "end_index", "?")
            print(f"[{i}] {title} - {url} (chars: {start}-{end})")

    # 3. Inspect intermediate research steps
    print("\n=== INTERMEDIATE AGENT STEPS ===\n")
    for step in response.output:
        if getattr(step, "type", None) == "web_search_call":
            query = getattr(step, "action", {}).get("query") if hasattr(step, "action") else None
            print(f"- [Web Search] Query: {query}")
        elif getattr(step, "type", None) == "reasoning":
            summaries = [s.text for s in getattr(step, "summary", []) if hasattr(s, "text")]
            print(f"- [Reasoning] {summaries}")
        elif getattr(step, "type", None) == "code_interpreter_call":
            print(f"- [Code Interpreter] Executed code step")

    return response


if __name__ == "__main__":
    run_deep_research()

