

# Retrieval-Augmented Generation (RAG) Pattern (Google ADK)

This directory implements the **Retrieval-Augmented Generation (RAG)** pattern using the **Google Agent Development Kit (ADK)** (`google-adk`) and Gemini foundation models across two grounding approaches:
1. **Dynamic Web Grounding (`adk_google_search.py`)**: Real-time web retrieval via the built-in `google_search` grounding tool.
2. **Managed RAG Memory Service (`adk_vertexAiRagMemoryService.py`)**: Persistent enterprise conversation and document memory using a dedicated **Vertex AI RAG Engine corpus**.

---

## Pattern Overview

The **Retrieval-Augmented Generation (RAG)** pattern enables models to retrieve relevant external knowledge dynamically before synthesizing answers. This avoids hallucinations, incorporates post-training information, and grounds model responses in authoritative source documents.

| Implementation | Framework & Grounding Source | Primary Use Case |
| :--- | :--- | :--- |
| `adk_google_search.py` | Google ADK + Google Search (`google_search`) | Live web search, news, current events, public information |
| `adk_vertexAiRagMemoryService.py` | Google ADK + Vertex AI RAG Engine (`VertexAiRagMemoryService`) | Enterprise knowledge bases, persistent conversation history, cross-session recall |
| `langchain_rag.py` | LangChain + LangGraph + Gemini LLM (`ChatGoogleGenerativeAI`) | Graph-based document chunking, semantic retrieval, and response synthesis |

---

## Agent Flows & Architectures

### 1. Dynamic Web Grounding Flow (`adk_google_search.py`)

```text
User Query
    │
    ▼
[Google ADK Agent: research_assistant]  (gemini-2.5-flash)
    │
    ▼
[Tool: google_search]
    ├── Dispatches web search queries via Google Search Grounding
    └── Retrieves web grounding chunks and citations
    │
    ▼
[Agent Synthesizes Grounded Answer with Sources]
```

### 2. Vertex AI RAG Memory Service Flow (`adk_vertexAiRagMemoryService.py`)

```text
Session 1 (Store)                          Session 2 (Recall)
──────────────────                         ──────────────────
User Prompt (Save Info)                    User Prompt (Recall Info)
       │                                          │
       ▼                                          ▼
[Google ADK Agent]                         [Google ADK Agent]
       │                                          │
       ▼                                          ▼
[Tool: save_to_rag_memory]                 [Tool: recall_from_rag_memory]
       │                                          │
       ▼                                          ▼
[tool_context.add_session_to_memory()]     [tool_context.search_memory()]
       │                                          │
       ▼ (Upload Transcript)                      ▼ (Semantic Search)
┌──────────────────────────────────────────────────────────────┐
│  Vertex AI RAG Engine Corpus (us-central1, Serverless)       │
│  projects/your-project-id/locations/us-central1/...         │
└──────────────────────────────────────────────────────────────┘
```

---

## File Structure

```text
pattern/rag/
├── README.md                          # Documentation and architecture guide
├── adk_google_search.py               # Live web search grounding agent (Google ADK)
├── adk_vertexAiRagMemoryService.py     # Vertex AI RAG Engine memory service agent (Google ADK)
├── langchain_rag.py                   # Graph-based RAG pipeline using Gemini LLM (LangChain + LangGraph)
├── pyproject.toml                     # Project dependencies
└── .env                               # Credentials & RAG corpus resource configuration
```

---

## 1. Google Search Grounding (`adk_google_search.py`)

- **Agent Definition (`search_agent`)**:
  ```python
  search_agent = Agent(
      name="research_assistant",
      model=MODEL_NAME,
      instruction="You help users research topics. When asked, use the Google Search tool",
      tools=[google_search]
  )
  ```
- **Runner (`InMemoryRunner`)**:
  Manages session creation, message dispatch, and agent execution lifecycle.
- **Execution Helper (`call_agent`)**:
  Streams execution events from `runner.run_async(...)`, inspects `event.grounding_metadata.web_search_queries` to observe generated search queries, and extracts the final grounded response.

---

## 2. Vertex AI RAG Memory Service (`adk_vertexAiRagMemoryService.py`)

- **Memory Service Configuration (`VertexAiRagMemoryService`)**:
  Connects to a Vertex AI RAG Corpus for semantic knowledge indexing and retrieval:
  ```python
  memory_service = VertexAiRagMemoryService(
      rag_corpus=RAG_CORPUS_RESOURCE_NAME,
      similarity_top_k=SIMILARITY_TOP_K,
      vector_distance_threshold=VECTOR_DISTANCE_THRESHOLD,
  )
  ```
- **Agent Tools (`recall_from_rag_memory` & `save_to_rag_memory`)**:
  - `recall_from_rag_memory`: Uses `tool_context.search_memory(query=...)` to retrieve relevant document chunks from the RAG corpus.
  - `save_to_rag_memory`: Uses `tool_context.add_session_to_memory()` to ingest the active conversation transcript into the RAG corpus for cross-session recall.
- **Runner (`Runner`)**:
  Binds `rag_memory_agent`, `InMemorySessionService`, and `VertexAiRagMemoryService` together.

---

## 3. LangChain + LangGraph RAG with Gemini LLM (`langchain_rag.py`)

- **Gemini LLM & Embeddings**:
  Powered by `ChatGoogleGenerativeAI` (`gemini-2.5-flash`) and `GoogleGenerativeAIEmbeddings` (`models/gemini-embedding-001`).
- **In-Memory Vector Store**:
  Uses `InMemoryVectorStore` to index document chunks and retrieve top matches without external database dependencies.
- **LangGraph State Graph**:
  Orchestrates retrieval and generation through a typed state graph (`retrieve` -> `generate` -> `END`).

---

## Step-by-Step Guide: Creating a Vertex AI RAG Engine Corpus

Follow these steps to create and configure a managed **Vertex AI RAG Engine corpus** in Google Cloud:

### 1. Prerequisites & Environment Setup
Define your project and target region (e.g., `us-central1`):
```bash
export PROJECT_ID="your-project-id"
export LOCATION="us-central1"
export PROJECT_NUMBER="$(gcloud projects describe ${PROJECT_ID} --format='value(projectNumber)')"
```

### 2. Enable Required Google Cloud APIs
Vertex AI RAG Engine requires both the core Vertex AI and Vector Search APIs:
```bash
gcloud services enable aiplatform.googleapis.com vectorsearch.googleapis.com --project "${PROJECT_ID}"
```

### 3. Grant Service Agent Permissions
When operating in serverless mode, Vertex AI and RAG service agents require `roles/vectorsearch.admin` to manage underlying vector collections:
```bash
# Vertex AI core service agent
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-aiplatform.iam.gserviceaccount.com" \
  --role="roles/vectorsearch.admin" \
  --condition=None

# Vertex RAG service agent
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-vertex-rag.iam.gserviceaccount.com" \
  --role="roles/vectorsearch.admin" \
  --condition=None
```

### 4. Configure RAG Engine to Serverless Mode
In `us-central1`, set the regional `ragEngineConfig` backend to Serverless mode (`ragManagedVertexVectorSearch`):

**Via Python:**
```python
from agentplatform import Client, types

client = Client(project=PROJECT_ID, location=LOCATION)
client.rag.update_config(
    updated_config=types.RagEngineConfig(
        name=f"projects/{PROJECT_ID}/locations/{LOCATION}/ragEngineConfig",
        rag_managed_db_config=types.RagManagedDbConfig(
            serverless=types.RagManagedDbConfigServerless()
        ),
    )
)
```

**Via REST (cURL):**
```bash
curl -X PATCH \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  "https://${LOCATION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT_ID}/locations/${LOCATION}/ragEngineConfig" \
  -d '{"ragManagedDbConfig": {"serverless": {}}}'
```

### 5. Create the RAG Corpus
Create the corpus using `agentplatform.Client`. By default, this uses Google's `text-embedding-005` (768 dimensions):

```python
from agentplatform import Client, types

client = Client(project=PROJECT_ID, location=LOCATION)

# Provision corpus
corpus = client.rag.create_corpus(
    rag_corpus=types.RagCorpus(
        display_name="adk-rag-memory-corpus",
        description="Vertex AI RAG Engine corpus for ADK memory service",
    )
)

print(f"Corpus Name: {corpus.name}")
# Output: projects/<project-number>/locations/us-central1/ragCorpora/<corpus-id>
```

### 6. Verify Corpus Status
List all corpora in the project to verify creation and retrieve the corpus ID:
```python
from agentplatform import Client

client = Client(project=PROJECT_ID, location=LOCATION)
response = client.rag.list_corpora()

for corpus in response.rag_corpora or []:
    print(f"Name        : {corpus.name}")
    print(f"Display Name: {corpus.display_name}")
    print(f"Embedding   : {corpus.rag_embedding_model_config.vertex_prediction_endpoint.endpoint}")
```

---

## Active Vertex AI RAG Corpus Details

The managed RAG corpus provisioned and configured for this repository:

| Attribute | Value |
| :--- | :--- |
| **Project** | `your-project-id` |
| **Location** | `us-central1` |
| **Corpus ID** | `your-corpus-id` |
| **Full Resource Name** | `projects/your-project-id/locations/us-central1/ragCorpora/your-corpus-id` |
| **Display Name** | `adk-rag-memory-corpus` |
| **Embedding Model** | `text-embedding-005` (768 dimensions) |
| **Vector DB Mode** | Serverless (`RagManagedVertexVectorSearch`) |

---

## Prerequisites & Setup

Ensure `uv` is installed, and your `.env` contains valid credentials:

```bash
GEMINI_MODEL_NAME=gemini-2.5-flash
GOOGLE_API_KEY=your_gemini_api_key_here
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
RAG_CORPUS_RESOURCE_NAME=projects/your-project-id/locations/us-central1/ragCorpora/your-corpus-id
```

Install dependencies:

```bash
cd /home/ollama/python/pattern/rag
uv sync
```

---

## How to Run

### 1. Run the Google Search RAG Agent:
```bash
cd /home/ollama/python/pattern/rag
uv run python adk_google_search.py
# or
.venv/bin/python adk_google_search.py
```

### 2. Run the Vertex AI RAG Memory Service Agent:
```bash
cd /home/ollama/python/pattern/rag
uv run python adk_vertexAiRagMemoryService.py
# or
.venv/bin/python adk_vertexAiRagMemoryService.py
```

### 3. Run the LangChain + LangGraph Gemini RAG Pipeline:
```bash
cd /home/ollama/python/pattern/rag
uv run python langchain_rag.py
# or
.venv/bin/python langchain_rag.py
```

---

## Sample Execution Traces

### Google Search Grounding (`adk_google_search.py`)
```text
💬 [User Query]: 'What are the latest updates and milestones on NASA's Artemis program?'
🔍 [Google Search Query]: NASA Artemis program latest updates
🔍 [Google Search Query]: NASA Artemis program milestones 2026

🤖 [Agent Response]:
NASA's Artemis program continues to advance:
- Artemis I (Nov 2022): Uncrewed flight test of SLS and Orion.
- Artemis II (Apr 2026): First crewed lunar flyby with Wiseman, Glover, Koch, and Hansen.
- Artemis III (Late 2027): Earth-orbit test of commercial lander docking systems.
- Artemis IV (Early 2028): First crewed lunar landing since Apollo 17.
```

### Vertex AI RAG Memory Service (`adk_vertexAiRagMemoryService.py`)
```text
💬 [Session 1]: 'Please note that our infrastructure deployed a Kubernetes cluster in us-central1 with 5 worker nodes running Gemini Enterprise RAG microservices. Please save this session into Vertex AI RAG memory.'
⚙️  [Agent Invoked Tool]: save_to_rag_memory
💾 [Tool Call: save_to_rag_memory] Ingesting session into RAG corpus...
   POST https://us-central1-aiplatform.googleapis.com/.../ragFiles:upload [HTTP 200 OK]
🤖 [Agent Response]: This session has been saved to your Vertex AI RAG memory.

💬 [Session 2 (New Session)]: 'What infrastructure and cluster details did I save in my previous session?'
⚙️  [Agent Invoked Tool]: recall_from_rag_memory
🔍 [Tool Call: recall_from_rag_memory] Searching for: 'infrastructure and cluster details'
   POST https://us-central1-aiplatform.googleapis.com/.../:retrieveContexts [HTTP 200 OK]
🤖 [Agent Response]: In a previous session, you saved that your infrastructure deployed a Kubernetes cluster in us-central1 with 5 worker nodes running Gemini Enterprise RAG microservices.
```

