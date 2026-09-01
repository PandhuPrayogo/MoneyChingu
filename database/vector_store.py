import json
import uuid
import math
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import VECTOR_DB_PATH, EMBEDDING_MODEL, GEMINI_API_KEY
from database.db import db

class VectorStore:
    """
    RAG Vector Store for semantic search over transactions, receipts, and notes.
    Uses Google text-embedding-004 when Gemini API is active, with cosine similarity retrieval.
    """
    def __init__(self, storage_path: Path = VECTOR_DB_PATH):
        self.storage_path = storage_path
        self.documents: List[Dict[str, Any]] = []
        self._load_documents()

    def _load_documents(self):
        """Load stored documents and embeddings from disk."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    self.documents = json.load(f)
            except Exception:
                self.documents = []
        else:
            self.documents = []

    def _save_documents(self):
        """Persist documents and embeddings to disk."""
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.documents, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving vector store: {e}")

    def clear_all(self):
        """Clear all stored vectors and reset memory to zero."""
        self.documents = []
        self._save_documents()

    def generate_embedding(self, text: str) -> List[float]:
        """Generate text embedding using Google Generative AI or deterministic fallback."""
        if GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=GEMINI_API_KEY)
                result = genai.embed_content(
                    model=EMBEDDING_MODEL,
                    content=text,
                    task_type="retrieval_document"
                )
                return result["embedding"]
            except Exception as e:
                # Fallback on failure
                pass

        # Deterministic lightweight pseudo-embedding based on hash & character frequencies
        return self._fallback_embedding(text)

    def _fallback_embedding(self, text: str, dim: int = 128) -> List[float]:
        """Simple deterministic term-frequency embedding fallback."""
        vec = [0.0] * dim
        tokens = text.lower().split()
        for token in tokens:
            h = hash(token) % dim
            vec[h] += 1.0
        # Normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    def add_document(self, text: str, metadata: Optional[Dict[str, Any]] = None, doc_type: str = "receipt", ref_id: Optional[str] = None) -> str:
        """Add and index a financial document/receipt/note."""
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        embedding = self.generate_embedding(text)
        
        doc_entry = {
            "id": doc_id,
            "ref_id": ref_id,
            "doc_type": doc_type,
            "text": text,
            "embedding": embedding,
            "metadata": metadata or {}
        }
        
        self.documents.append(doc_entry)
        self._save_documents()
        return doc_id

    def search(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Semantic similarity search against stored financial documents."""
        if not self.documents:
            return []

        query_emb = self.generate_embedding(query)
        q_vec = np.array(query_emb, dtype=np.float32)
        
        results = []
        for doc in self.documents:
            d_vec = np.array(doc["embedding"], dtype=np.float32)
            # Cosine similarity
            dot = np.dot(q_vec, d_vec)
            norm_q = np.linalg.norm(q_vec)
            norm_d = np.linalg.norm(d_vec)
            sim = float(dot / (norm_q * norm_d)) if (norm_q > 0 and norm_d > 0) else 0.0
            
            results.append({
                "id": doc["id"],
                "text": doc["text"],
                "doc_type": doc["doc_type"],
                "metadata": doc["metadata"],
                "similarity_score": round(sim, 4)
            })

        # Sort by similarity descending
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results[:top_k]

# Global singleton
vector_store = VectorStore()
