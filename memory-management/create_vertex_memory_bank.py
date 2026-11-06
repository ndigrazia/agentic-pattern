import os
import sys
import warnings
from dotenv import load_dotenv

warnings.filterwarnings("ignore", category=FutureWarning)

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("PROJECT_ID")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
DISPLAY_NAME = os.getenv("AGENT_ENGINE_DISPLAY_NAME", "adk-memory-bank-engine")


def create_memory_bank_engine():
    """Provisions a new Vertex AI Agent Engine with Memory Bank enabled."""
    if not PROJECT_ID:
        print("❌ Error: Missing Google Cloud Project ID.")
        print("Please set GOOGLE_CLOUD_PROJECT or PROJECT_ID in your .env file or environment.")
        sys.exit(1)

    try:
        import vertexai
    except ImportError:
        print("❌ Error: vertexai is not installed.")
        print("Install it using: uv pip install google-cloud-aiplatform")
        sys.exit(1)

    print("Connecting to Vertex AI...")
    print(f"  Project : {PROJECT_ID}")
    print(f"  Location: {LOCATION}")
    print(f"  Engine  : {DISPLAY_NAME}")

    try:
        client = vertexai.Client(project=PROJECT_ID, location=LOCATION)

        print("\nCreating Vertex AI Memory Bank (Agent Engine)...")
        engine = client.agent_engines.create(
            config={
                "display_name": DISPLAY_NAME,
                "context_spec": {
                    "memory_bank_config": {}
                },
            }
        )

        resource_name = engine.api_resource.name
        engine_id = resource_name.split("/")[-1]

        print("\n=======================================================")
        print("✅ Vertex AI Memory Bank Created Successfully!")
        print(f"Resource Name: {resource_name}")
        print(f"Agent Engine ID: {engine_id}")
        print("=======================================================")
        print("\nNext step: Add this ID to your `.env` file:")
        print(f"AGENT_ENGINE_ID={engine_id}")
        print(f"GOOGLE_CLOUD_PROJECT={PROJECT_ID}")
        print(f"GOOGLE_CLOUD_LOCATION={LOCATION}")
        print("\nThen run your ADK Memory Bank application:")
        print("uv run adk_vertex_memory_bank.py")
        print("=======================================================")

        return engine_id

    except Exception as e:
        print(f"\n❌ Failed to create Vertex AI Memory Bank: {e}")
        print("\nTroubleshooting tips:")
        print("1. Ensure Vertex AI API is enabled:")
        print(f"   gcloud services enable aiplatform.googleapis.com --project {PROJECT_ID}")
        print("2. Ensure you have authenticated with Google Cloud:")
        print("   gcloud auth application-default login")
        print("3. Check IAM permissions: Vertex AI Administrator or Vertex AI User.")
        sys.exit(1)


def list_existing_engines():
    """Lists existing Agent Engine resources in the project."""
    if not PROJECT_ID:
        print("❌ Error: Missing GOOGLE_CLOUD_PROJECT or PROJECT_ID.")
        sys.exit(1)
    try:
        import vertexai
        client = vertexai.Client(project=PROJECT_ID, location=LOCATION)
        print(f"\nExisting Agent Engines in {PROJECT_ID} ({LOCATION}):")
        count = 0
        for engine in client.agent_engines.list():
            eng_id = engine.api_resource.name.split("/")[-1]
            display = getattr(engine.api_resource, "display_name", "N/A")
            print(f" - ID: {eng_id} | Display: {display}")
            count += 1
        if count == 0:
            print(" (None found)")
    except Exception as e:
        print(f"Could not list engines: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        list_existing_engines()
    else:
        create_memory_bank_engine()

