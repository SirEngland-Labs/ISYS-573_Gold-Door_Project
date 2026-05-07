"""RAG knowledge base — indexes restaurant info for FAQ retrieval."""

import os
from pathlib import Path
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

# Path to knowledge files
KNOWLEDGE_DIR = os.environ.get("KNOWLEDGE_DIR", "knowledge")

# Global vector store — initialized once
_vector_store = None


def _load_documents():
    """Load all markdown files from the knowledge directory."""
    docs = []
    knowledge_path = Path(KNOWLEDGE_DIR)

    for md_file in knowledge_path.glob("*.md"):
        loader = TextLoader(str(md_file), encoding="utf-8")
        file_docs = loader.load()
        # Tag each document with its source file
        for doc in file_docs:
            doc.metadata["source"] = md_file.stem  # "menu", "hours", "policies"
        docs.extend(file_docs)

    return docs


def _build_index():
    """Build FAISS index from knowledge documents."""
    global _vector_store

    docs = _load_documents()
    if not docs:
        raise ValueError(f"No documents found in {KNOWLEDGE_DIR}/")

    # Split into chunks — small chunks for precise retrieval
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
        separators=["\n## ", "\n### ", "\n- ", "\n\n", "\n", " "]
    )
    chunks = splitter.split_documents(docs)

    # Use a small, fast embedding model — runs locally, no API needed
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"}
    )

    _vector_store = FAISS.from_documents(chunks, embeddings)
    return _vector_store


def get_vector_store():
    """Get or create the FAISS vector store."""
    global _vector_store
    if _vector_store is None:
        _build_index()
    return _vector_store


def search_knowledge(query: str, k: int = 3) -> str:
    """Search the knowledge base and return relevant info.

    Args:
        query: Customer's question (e.g., "what desserts do you have?")
        k: Number of results to return

    Returns:
        Formatted string of relevant knowledge chunks.
    """
    store = get_vector_store()
    results = store.similarity_search(query, k=k)

    if not results:
        return "No relevant information found."

    # Format results with source labels
    formatted = []
    for doc in results:
        source = doc.metadata.get("source", "unknown")
        formatted.append(f"[{source}] {doc.page_content.strip()}")

    return "\n\n".join(formatted)


def reload_knowledge():
    """Reload the knowledge base — call after knowledge files are updated."""
    global _vector_store
    _vector_store = None
    _build_index()
