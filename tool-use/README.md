# Vertex AI Search - Data Store Creation Guide (gcloud & REST)

Comprehensive guide to provisioning, configuring, and managing **Vertex AI Search (Discovery Engine)** data stores via the CLI using `gcloud` and the Discovery Engine REST API.

---

## Table of Contents

- [What is Vertex AI Search?](#what-is-vertex-ai-search)
  - [How It Works](#how-it-works)
  - [Resource Hierarchy](#resource-hierarchy)
  - [Vertex AI Search vs. Vector Search](#vertex-ai-search-vs-vector-search)
- [Prerequisites & Authentication](#prerequisites--authentication)
- [API Endpoints & Regionality](#api-endpoints--regionality)
- [Step 1: Environment Configuration](#step-1-environment-configuration)
- [Step 2: Create Data Store](#step-2-create-data-store)
  - [Option A: Unstructured Data (PDF, Docs, HTML, TXT)](#option-a-unstructured-data-pdf-docs-html-txt)
  - [Option B: Structured Data (BigQuery, JSON Lines)](#option-b-structured-data-bigquery-json-lines)
  - [Option C: Website Search (Public Web Domains)](#option-c-website-search-public-web-domains)
  - [Option D: Custom Chunking & OCR Parsing](#option-d-custom-chunking--ocr-parsing)
- [Step 3: Document Ingestion (Local File & GCS)](#step-3-document-ingestion-local-file--gcs)
  - [Ingest Local File (e.g., ai_data.txt) via GCS](#ingest-local-file-eg-ai_datatxt-via-gcs)
  - [Ingest from Google Cloud Storage (GCS) Batch](#ingest-from-google-cloud-storage-gcs-batch)
  - [Ingest from Google BigQuery](#ingest-from-google-bigquery)
- [Step 4: Manage & Inspect Data Stores](#step-4-manage--inspect-data-stores)
- [Step 5: Query & Search Verification](#step-5-query--search-verification)
- [Google ADK Agent Integration (vsearch_app.py)](#google-adk-agent-integration-vsearch_apppy)
- [Python SDK Alternative](#python-sdk-alternative)
- [Troubleshooting & Best Practices](#troubleshooting--best-practices)

---

## What is Vertex AI Search?

**Vertex AI Search** (formerly *Generative AI App Builder / Enterprise Search*) is a fully-managed, turnkey enterprise search and discovery service built on Google's Discovery Engine (`discoveryengine.googleapis.com`). It allows organizations to build Google-grade semantic search, conversational search, and generative question-answering applications directly over internal and external data stores.

### How It Works

1. **Ingestion & Auto-Parsing:** Connects to Cloud Storage, BigQuery, Google Drive, websites, Jira, and more. It parses documents (PDFs, Word, HTML, text) and performs automatic OCR on scanned files.
2. **Chunking & Semantic Indexing:** Splits documents into manageable chunks and indexes them with dense embeddings and lexical indices—no manual embedding pipeline or vector database management required.
3. **Hybrid Search & Ranking:** Combines vector similarity with keyword search and applies Google's deep ranking algorithms to order results by topicality and semantic relevance.
4. **Generative Grounding:** Powers Retrieval-Augmented Generation (RAG) by directly feeding verified passages to foundation models (Gemini), producing answers with traceable, inline citations.

### Resource Hierarchy

```text
projects/{project_id}
  └── locations/{location}               (global, us, eu)
        └── collections/default_collection
              └── dataStores/{data_store_id}
                    ├── servingConfigs/default_search
                    └── branches/0       (default active branch)
                          └── documents/{document_id}
```

> **Note on `gcloud` CLI**: Google Cloud SDK does not expose a native high-level CLI command (e.g., `gcloud discoveryengine data-stores create`). The official CLI method is using `curl` authenticated with bearer tokens from `$(gcloud auth print-access-token)`.
>
> *(Note: The command `gcloud datastore` manages Cloud Datastore / Firestore in Datastore mode, and is unrelated to Vertex AI Search).*

### Vertex AI Search vs. Vector Search

| Capability | Vertex AI Search (Discovery Engine) | Vertex AI Vector Search (Matching Engine) |
| :--- | :--- | :--- |
| **Nature** | Turnkey Search & RAG platform | Low-level, high-speed vector database |
| **Data Input** | Raw documents (PDF, TXT, HTML, tables) | Pre-computed dense vector embeddings |
| **Chunking/Embedding** | Automatic & managed | Manual developer responsibility |
| **Ranking** | Hybrid (Semantic + BM25 + Google Ranker) | ANN Vector Distance (Cosine / Dot / Euclidean) |
| **Best For** | Enterprise document search, RAG, knowledge bases | Custom embedding matching, recommendation vectors |

---

## Prerequisites & Authentication

### 1. Install & Authenticate `gcloud`

```bash
# Verify gcloud installation
gcloud version

# Authenticate your user account
gcloud auth login

# Set application default credentials (for SDK scripts)
gcloud auth application-default login
```

### 2. Required IAM Permissions

Ensure the calling identity has one of the following IAM roles on the GCP project:
- `roles/discoveryengine.admin` (Discovery Engine Admin)
- `roles/discoveryengine.editor` (Discovery Engine Editor)

### 3. Enable Required APIs

```bash
gcloud services enable discoveryengine.googleapis.com
```

---

## API Endpoints & Regionality

| Location | API Host Endpoint |
| :--- | :--- |
| **Multi-region (global)** | `https://discoveryengine.googleapis.com` |
| **US Multi-region (`us`)** | `https://us-discoveryengine.googleapis.com` |
| **EU Multi-region (`eu`)** | `https://eu-discoveryengine.googleapis.com` |

---

## Step 1: Environment Configuration

Export the necessary shell variables:

```bash
# Target GCP Project ID
export PROJECT_ID="$(gcloud config get-value project)"

# Target Location: 'global', 'us', or 'eu'
export LOCATION="global"

# Unique Data Store Identifier (lowercase letters, numbers, hyphens, underscores)
export DATA_STORE_ID="kb-search-store"

# Human-readable Display Name
export DISPLAY_NAME="Knowledge Base Search Store"

# Base API URL
if [ "$LOCATION" = "global" ]; then
  export API_ENDPOINT="https://discoveryengine.googleapis.com"
else
  export API_ENDPOINT="https://${LOCATION}-discoveryengine.googleapis.com"
fi
```

---

## Step 2: Create Data Store

### Option A: Unstructured Data (PDF, Docs, HTML, TXT)

For document search with unstructured files. Sets `contentConfig` to `CONTENT_REQUIRED`.

```bash
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "${API_ENDPOINT}/v1/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/dataStores?dataStoreId=${DATA_STORE_ID}" \
  -d '{
    "displayName": "'"${DISPLAY_NAME}"'",
    "industryVertical": "GENERIC",
    "solutionTypes": ["SOLUTION_TYPE_SEARCH"],
    "contentConfig": "CONTENT_REQUIRED"
  }'
```

---

### Option B: Structured Data (BigQuery, JSON Lines)

For structured records or tabular schemas. Sets `contentConfig` to `NO_CONTENT`.

```bash
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "${API_ENDPOINT}/v1/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/dataStores?dataStoreId=${DATA_STORE_ID}" \
  -d '{
    "displayName": "'"${DISPLAY_NAME}"'",
    "industryVertical": "GENERIC",
    "solutionTypes": ["SOLUTION_TYPE_SEARCH"],
    "contentConfig": "NO_CONTENT"
  }'
```

---

### Option C: Website Search (Public Web Domains)

For crawling domain URLs and public web assets. Sets `contentConfig` to `PUBLIC_WEBSITE`.

```bash
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "${API_ENDPOINT}/v1/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/dataStores?dataStoreId=${DATA_STORE_ID}" \
  -d '{
    "displayName": "'"${DISPLAY_NAME}"'",
    "industryVertical": "GENERIC",
    "solutionTypes": ["SOLUTION_TYPE_SEARCH"],
    "contentConfig": "PUBLIC_WEBSITE"
  }'
```

---

### Option D: Custom Chunking & OCR Parsing

To enable OCR for scanned documents and configure custom chunking parameters (e.g., 500 token chunks with 100 token overlap) using the `v1alpha` API:

```bash
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "${API_ENDPOINT}/v1alpha/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/dataStores?dataStoreId=${DATA_STORE_ID}" \
  -d '{
    "displayName": "'"${DISPLAY_NAME}"'",
    "industryVertical": "GENERIC",
    "solutionTypes": ["SOLUTION_TYPE_SEARCH"],
    "contentConfig": "CONTENT_REQUIRED",
    "documentProcessingConfig": {
      "defaultParsingConfig": {
        "ocrParsingConfig": {
          "useNativeText": true
        }
      },
      "chunkingConfig": {
        "layoutBasedChunkingConfig": {
          "chunkSize": 500,
          "includeAncestorHeadings": true
        }
      }
    }
  }'
```


---

## Step 3: Document Ingestion (Local File & GCS)

After creating the data store, ingest content into branch `0` (the default active branch).

### Ingest Local File (e.g., `ai_data.txt`) via GCS

For unstructured documents (`contentConfig: "CONTENT_REQUIRED"`), files must first be staged in a Google Cloud Storage bucket before triggering ingestion.

#### 1. Upload Local File to GCS:
```bash
export BUCKET_NAME="my-storage-bucket"
gcloud storage cp ai_data.txt "gs://${BUCKET_NAME}/vertex_ai_search/ai_data.txt"
```

#### 2. Trigger Ingestion Request:
```bash
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "${API_ENDPOINT}/v1/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/dataStores/${DATA_STORE_ID}/branches/0/documents:import" \
  -d '{
    "gcsSource": {
      "inputUris": ["gs://'"${BUCKET_NAME}"'/vertex_ai_search/ai_data.txt"],
      "dataSchema": "content"
    },
    "reconciliationMode": "INCREMENTAL"
  }'
```
> **Important:**
> - Use `"dataSchema": "content"` for raw unstructured text/documents (`.txt`, `.pdf`, `.html`, `.docx`).
> - Do not set `"autoGenerateIds": true` when using `"content"`, as IDs are automatically derived from the file URI.

#### 3. Monitor Import Operation:
The API returns a long-running operation name (e.g., `projects/.../operations/import-documents-XXXXX`). Poll its status:
```bash
curl -X GET \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "${API_ENDPOINT}/v1/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/dataStores/${DATA_STORE_ID}/branches/0/operations/<OPERATION_ID>"
```

---

### Ingest from Google Cloud Storage (GCS) Batch

For batch importing multiple documents from a bucket:

```bash
export GCS_URI="gs://my-documents-bucket/*.pdf"

curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "${API_ENDPOINT}/v1/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/dataStores/${DATA_STORE_ID}/branches/0/documents:import" \
  -d '{
    "gcsSource": {
      "inputUris": ["'"${GCS_URI}"'"],
      "dataSchema": "content"
    },
    "reconciliationMode": "INCREMENTAL"
  }'
```

---

### Ingest from Google BigQuery

```bash
export BQ_DATASET="my_dataset"
export BQ_TABLE="knowledge_articles"

curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "${API_ENDPOINT}/v1/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/dataStores/${DATA_STORE_ID}/branches/0/documents:import" \
  -d '{
    "bigquerySource": {
      "projectId": "'"${PROJECT_ID}"'",
      "datasetId": "'"${BQ_DATASET}"'",
      "tableId": "'"${BQ_TABLE}"'",
      "dataSchema": "custom"
    },
    "reconciliationMode": "INCREMENTAL",
    "autoGenerateIds": true
  }'
```

---

## Step 4: Manage & Inspect Data Stores

### Get Data Store Details

```bash
curl -X GET \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "${API_ENDPOINT}/v1/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/dataStores/${DATA_STORE_ID}"
```

### List Documents in Data Store (Branch 0)

Check parsed and indexed documents along with their `indexTime` status:

```bash
curl -X GET \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "${API_ENDPOINT}/v1/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/dataStores/${DATA_STORE_ID}/branches/0/documents"
```

### List All Data Stores

```bash
curl -X GET \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "${API_ENDPOINT}/v1/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/dataStores"
```

### Delete Data Store (Cleanup)

To permanently delete a data store and all of its indexed documents:

```bash
curl -X DELETE \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "${API_ENDPOINT}/v1/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/dataStores/${DATA_STORE_ID}"
```

#### Expected Response:
```json
{
  "name": "projects/.../locations/global/collections/default_collection/operations/delete-data-store-XXXXX",
  "done": true
}
```

#### Verify Deletion:
Running a `GET` on the deleted data store will return a `404 Not Found`:
```bash
curl -X GET \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "${API_ENDPOINT}/v1/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/dataStores/${DATA_STORE_ID}"
```
```json
{
  "error": {
    "code": 404,
    "message": "Data store ... not found.",
    "status": "NOT_FOUND"
  }
}
```

*(Optional)* Clean up the staged file from Google Cloud Storage:
```bash
gcloud storage rm "gs://${BUCKET_NAME}/vertex_ai_search/ai_data.txt"
```

---

## Step 5: Query & Search Verification

Once documents are indexed, execute semantic and keyword search queries against the `default_search` serving config:

```bash
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "${API_ENDPOINT}/v1/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/dataStores/${DATA_STORE_ID}/servingConfigs/default_search:search" \
  -d '{
    "query": "Retrieval Augmented Generation chunking strategies",
    "pageSize": 5
  }'
```

#### Sample Response:
```json
{
  "results": [
    {
      "id": "f346ecf0b2b766dac1fec838b07a2976",
      "document": {
        "name": "projects/.../documents/f346ecf0b2b766dac1fec838b07a2976",
        "derivedStructData": {
          "title": "ai_data",
          "link": "gs://my-storage-bucket/vertex_ai_search/ai_data.txt"
        }
      },
      "rankSignals": {
        "keywordSimilarityScore": 1.09,
        "semanticSimilarityScore": 0.72
      }
    }
  ],
  "totalSize": 1
}
```

---
---

## Google ADK Agent Integration (vsearch_app.py)

You can connect Google's Agent Development Kit (**Google ADK**) to Vertex AI Search using `FunctionTool` to create an autonomous search agent that grounds responses in `my-search-datastore`.

### Agent Architecture

```text
User Query
    │
    ▼
[Google ADK Agent]  (gemini-2.5-flash)
    │
    │ (Tool Call Reasoning)
    ▼
[FunctionTool: search_datastore]
    │
    │ (SearchRequest with SnippetSpec)
    ▼
[Vertex AI Search: my-search-datastore]
    │
    │ (Excerpts, Titles, GCS Source Links)
    ▼
[Agent Synthesizes Grounded Answer with Citations]
```

### Running the Agent

The runnable script is available at `vsearch_app.py`:

```bash
# Execute using uv
uv run python vsearch_app.py
```

### Sample Agent Execution Trace

```text
🚀 Initializing Google ADK Agent with Vertex AI Search (my-search-datastore)...

==================================================
💬 [User Query]: 'What chunking strategies are described for Retrieval-Augmented Generation (RAG)?'
==================================================
⚙️  [Agent Decided to Call Tool]: search_datastore
🔍 [Tool Call: search_datastore] Querying: 'chunking strategies RAG'
📥 [Received Tool Response for]: search_datastore

🤖 [Agent Final Answer]:
Based on the internal documentation, the chunking strategies described for Retrieval-Augmented Generation (RAG) divide documents into manageable chunks using methods such as:

* **Recursive character splitting**
* **Semantic boundary chunking**
* **Token-limited chunking**

---
**Source:**
* **Document Title:** ai_data
* **Source URI:** gs://tma-gemini-enterprise-agent-staging/vertex_ai_search/ai_data.txt
```


## Python SDK Alternative

For programmatic automation via Python:

```bash
pip install google-cloud-discoveryengine
```

```python
from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine

def create_data_store(
    project_id: str,
    location: str = "global",
    data_store_id: str = "my-search-datastore",
    display_name: str = "My Search Data Store",
) -> str:
    # 1. Configure endpoint for multi-region or regional instance
    client_options = (
        ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
        if location != "global"
        else None
    )

    client = discoveryengine.DataStoreServiceClient(client_options=client_options)

    # 2. Build parent path
    parent = client.collection_path(
        project=project_id,
        location=location,
        collection="default_collection",
    )

    # 3. Define Data Store configuration
    data_store = discoveryengine.DataStore(
        display_name=display_name,
        industry_vertical=discoveryengine.IndustryVertical.GENERIC,
        solution_types=[discoveryengine.SolutionType.SOLUTION_TYPE_SEARCH],
        content_config=discoveryengine.DataStore.ContentConfig.CONTENT_REQUIRED,
    )

    request = discoveryengine.CreateDataStoreRequest(
        parent=parent,
        data_store_id=data_store_id,
        data_store=data_store,
    )

    # 4. Execute long-running operation
    operation = client.create_data_store(request=request)
    print(f"Creating data store operation: {operation.operation.name}")
    response = operation.result()
    print(f"Data store successfully created: {response.name}")
    return response.name

if __name__ == "__main__":
    import os
    PROJECT = os.environ.get("PROJECT_ID", "your-project-id")
    create_data_store(project_id=PROJECT)
```

---

## Troubleshooting & Best Practices

| Issue / Error | Cause | Resolution |
| :--- | :--- | :--- |
| `403 Forbidden: API discoveryengine.googleapis.com has not been used` | API is disabled in project | Run `gcloud services enable discoveryengine.googleapis.com` |
| `400 Bad Request: X-Goog-User-Project is required` | Quota project header missing | Add `-H "X-Goog-User-Project: ${PROJECT_ID}"` to curl commands |
| `404 Not Found` on regional resource | Endpoint / location mismatch | Use `${LOCATION}-discoveryengine.googleapis.com` for regional locations (`us`, `eu`) |
| Data Store creation returns LRO | Creating a data store is asynchronous | Inspect long-running operation name via `GET ${API_ENDPOINT}/v1/{operation_name}` |
| `ALREADY_EXISTS` | Data store ID already in use | Pick a unique `dataStoreId` parameter or delete the existing one |

