import os
from typing import Any, Dict, List, TypedDict
from dotenv import load_dotenv
import requests

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from langgraph.graph import END, StateGraph

load_dotenv()

# --- 1. Model Configuration (Google Gemini) ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001")

# Initialize Gemini LLM and Embeddings
llm = ChatGoogleGenerativeAI(
    model=MODEL_NAME,
    google_api_key=GOOGLE_API_KEY,
    temperature=0,
)

embeddings = GoogleGenerativeAIEmbeddings(
    model=EMBEDDING_MODEL,
    google_api_key=GOOGLE_API_KEY,
)

# --- 2. Data Preparation (Preprocessing) ---
script_dir = os.path.dirname(os.path.abspath(__file__))
local_file = os.path.join(script_dir, "state_of_the_union.txt")
raw_url = "https://raw.githubusercontent.com/hwchase17/chroma-langchain/master/state_of_the_union.txt"

text_content = ""
if os.path.exists(local_file):
    with open(local_file, "r", encoding="utf-8") as f:
        text_content = f.read()
else:
    try:
        res = requests.get(raw_url, timeout=10)
        res.raise_for_status()
        text_content = res.text
        with open(local_file, "w", encoding="utf-8") as f:
            f.write(text_content)
    except Exception as e:
        print(f"Warning: Could not fetch from URL ({e}), using default sample text.")
        text_content = (
            "Tonight, I’d like to honor someone who has dedicated his life to serve this country: "
            "Justice Stephen Breyer—an Army veteran, Constitutional scholar, and retiring Justice "
            "of the United States Supreme Court. Justice Breyer, thank you for your service.\n\n"
            "Our economy created over 6.5 million new jobs last year, more jobs than in any year in American history."
        )

# Chunk documents
text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = text_splitter.create_documents([text_content])

# Embed and store chunks in an in-memory vector store
vectorstore = InMemoryVectorStore.from_documents(
    documents=chunks,
    embedding=embeddings,
)

# Define the retriever
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})


# --- 3. Define the State for LangGraph ---
class RAGGraphState(TypedDict):
    question: str
    documents: List[Document]
    generation: str


# --- 4. Define the Nodes (Functions) ---
def retrieve_documents_node(state: RAGGraphState) -> RAGGraphState:
    """Retrieves documents based on the user's question."""
    question = state["question"]
    documents = retriever.invoke(question)
    return {"documents": documents, "question": question, "generation": ""}


def generate_response_node(state: RAGGraphState) -> RAGGraphState:
    """Generates a response using Gemini LLM based on retrieved documents."""
    question = state["question"]
    documents = state["documents"]

    template = """You are an assistant for question-answering tasks.
Use the following pieces of retrieved context to answer the question.
If you don't know the answer, just say that you don't know.
Use three sentences maximum and keep the answer concise.
Question: {question}
Context: {context}
Answer:"""

    prompt = ChatPromptTemplate.from_template(template)
    context = "\n\n".join([doc.page_content for doc in documents])

    # Create the RAG chain with Gemini LLM
    rag_chain = prompt | llm | StrOutputParser()

    # Invoke the chain
    generation = rag_chain.invoke({"context": context, "question": question})

    return {"question": question, "documents": documents, "generation": generation}


# --- 5. Build the LangGraph Graph ---
workflow = StateGraph(RAGGraphState)

# Add nodes
workflow.add_node("retrieve", retrieve_documents_node)
workflow.add_node("generate", generate_response_node)

# Set the entry point
workflow.set_entry_point("retrieve")

# Add edges (transitions)
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", END)

# Compile the graph
app = workflow.compile()


# --- 6. Run the RAG Application ---
if __name__ == "__main__":
    print(f"=== LangChain + LangGraph RAG using Gemini LLM ({MODEL_NAME}) ===")

    print("\n--- Running RAG Query 1 ---")
    query_1 = "What did the president say about Justice Breyer?"
    print(f"Question: {query_1}")
    result_1 = app.invoke({"question": query_1})
    print(f"\nGenerated Answer:\n{result_1['generation']}")

    print("\n--- Running RAG Query 2 ---")
    query_2 = "What did the president say about the economy and job creation?"
    print(f"Question: {query_2}")
    result_2 = app.invoke({"question": query_2})
    print(f"\nGenerated Answer:\n{result_2['generation']}")
