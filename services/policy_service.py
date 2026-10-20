"""
Policy Retrieval Service using LangChain and FAISS.
Loads policy documents (TXT/PDF), chunks texts, computes embeddings,
stores in FAISS vector store, and retrieves relevant policy passages with citations.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from dotenv import load_dotenv

from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
POLICIES_DIR = BASE_DIR / "knowledge_base" / "policies"
VECTOR_STORE_DIR = BASE_DIR / "vector_store" / "faiss_policy_index"

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "models/text-embedding-004").strip()


class DeterministicPolicyEmbeddings(Embeddings):
    """
    Fast, deterministic bag-of-words embedding generator for offline/demo operation.
    Guarantees FAISS index functions without external API credentials or latency.
    """

    def __init__(self, dim: int = 128):
        self.dim = dim

    def _embed(self, text: str) -> List[float]:
        vec = np.zeros(self.dim, dtype=np.float32)
        words = re.findall(r"\w+", text.lower())
        for w in words:
            # Deterministic bucket assignment
            idx = abs(hash(w)) % self.dim
            vec[idx] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec.tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)


def get_embeddings_model() -> Tuple[Embeddings, bool]:
    """
    Return embeddings instance and a boolean indicating whether live Gemini is active.
    Falls back gracefully to DeterministicPolicyEmbeddings if no key is present or on API error.
    """
    if GOOGLE_API_KEY and not GOOGLE_API_KEY.startswith("your_api_key"):
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings

            emb = GoogleGenerativeAIEmbeddings(
                model=EMBEDDING_MODEL,
                google_api_key=GOOGLE_API_KEY,
            )
            # Test a probe query
            _ = emb.embed_query("test probe")
            return emb, True
        except Exception as e:
            print(f"Warning: Failed to initialize Google Generative AI Embeddings ({e}). Falling back to local.")

    return DeterministicPolicyEmbeddings(), False


def load_policy_documents() -> List[Document]:
    """Load text and PDF files from the policies folder."""
    POLICIES_DIR.mkdir(parents=True, exist_ok=True)
    documents = []

    for file_path in POLICIES_DIR.glob("*.*"):
        if file_path.suffix.lower() == ".txt":
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # Extract title if present
                title_match = re.search(r"DOCUMENT:\s*(.+)", content)
                doc_title = title_match.group(1).strip() if title_match else file_path.stem
                documents.append(
                    Document(
                        page_content=content,
                        metadata={"source": file_path.name, "title": doc_title, "file_path": str(file_path)},
                    )
                )
            except Exception as e:
                print(f"Error reading {file_path}: {e}")

        elif file_path.suffix.lower() == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(str(file_path))
                pdf_text = ""
                for page_num, page in enumerate(reader.pages):
                    pdf_text += f"\n--- Page {page_num + 1} ---\n" + (page.extract_text() or "")
                documents.append(
                    Document(
                        page_content=pdf_text,
                        metadata={"source": file_path.name, "title": file_path.stem, "file_path": str(file_path)},
                    )
                )
            except Exception as e:
                print(f"Error reading PDF {file_path}: {e}")

    return documents


def build_faiss_index(force_rebuild: bool = False) -> Optional[FAISS]:
    """
    Build or load FAISS vector store from policy documents.
    Preserves section chunks and document source metadata.
    """
    VECTOR_STORE_DIR.parent.mkdir(parents=True, exist_ok=True)
    embeddings, is_live = get_embeddings_model()

    # Load and chunk documents
    raw_docs = load_policy_documents()
    if not raw_docs:
        print("No policy documents found in knowledge_base/policies.")
        return None

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=80,
        separators=["\nSECTION ", "\n\n", "\n", " "],
    )

    split_docs = text_splitter.split_documents(raw_docs)

    # Attach section header to metadata if detectable
    for doc in split_docs:
        sec_match = re.search(r"(SECTION\s+\d+[:\s][^\n]+)", doc.page_content)
        if sec_match:
            doc.metadata["section"] = sec_match.group(1).strip()
        else:
            doc.metadata["section"] = "General Terms"

    # Create and persist FAISS index
    vector_store = FAISS.from_documents(split_docs, embeddings)
    try:
        vector_store.save_local(str(VECTOR_STORE_DIR))
    except Exception as e:
        print(f"Notice: FAISS save_local warning ({e}). Index retained in memory.")

    return vector_store


_cached_vector_store: Optional[FAISS] = None


def get_or_create_vector_store() -> Optional[FAISS]:
    """Retrieve cached vector store or build if needed."""
    global _cached_vector_store
    if _cached_vector_store is not None:
        return _cached_vector_store

    embeddings, _ = get_embeddings_model()

    if (VECTOR_STORE_DIR / "index.faiss").exists():
        try:
            _cached_vector_store = FAISS.load_local(
                str(VECTOR_STORE_DIR),
                embeddings,
                allow_dangerous_deserialization=True,
            )
            return _cached_vector_store
        except Exception:
            pass

    _cached_vector_store = build_faiss_index()
    return _cached_vector_store


def retrieve_relevant_policies(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Retrieve top relevant policy passages for a dispute or complaint.
    Returns list of dicts with content, source document, section, and score.
    """
    vector_store = get_or_create_vector_store()
    if not vector_store:
        return []

    try:
        results = vector_store.similarity_search_with_score(query, k=top_k)
        formatted = []
        for doc, score in results:
            formatted.append(
                {
                    "content": doc.page_content.strip(),
                    "source": doc.metadata.get("source", "Unknown Policy"),
                    "title": doc.metadata.get("title", doc.metadata.get("source", "Policy")),
                    "section": doc.metadata.get("section", "Standard Policy Section"),
                    "similarity_score": round(float(score), 4),
                }
            )
        return formatted
    except Exception as e:
        print(f"Error during policy retrieval: {e}")
        return []
