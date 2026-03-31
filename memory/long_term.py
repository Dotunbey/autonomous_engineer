#!memory/long_term.py
import json
import logging
import math
import os
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Generator
from memory.embeddings import EmbeddingEngine

logger = logging.getLogger(__name__)

@dataclass
class MemoryRecord:
    """Represents a single persistent memory (e.g., a past bug fix or playbook rule)."""
    id: str
    content: str
    vector: List[float]
    metadata: Dict[str, Any]

class LongTermMemory:
    """
    Vector-based storage for long-term agent learning.
    
    Stores successful execution patterns, resolved errors, and project constraints.
    In V40+, this acts as a wrapper around FAISS, ChromaDB, or pgvector.
    """

    def __init__(self, storage_path: str = "data/long_term_memory.json"):
        """
        Initializes the persistent memory storage.

        Args:
            storage_path: File path for local JSON fallback storage.
        """
        self._storage_path = storage_path
        self._engine = EmbeddingEngine()
        self._records: List[MemoryRecord] = []
        self._load_memory()

    def _load_memory(self) -> None:
        """Loads records from the persistent JSON file."""
        if not os.path.exists(self._storage_path):
            return
            
        try:
            with open(self._storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._records = [MemoryRecord(**record) for record in data]
            logger.info(f"Loaded {len(self._records)} memories from {self._storage_path}")
        except Exception as e:
            logger.error(f"Failed to load long-term memory: {e}")

    def _save_memory(self) -> None:
        """Persists current records to the JSON file."""
        try:
            os.makedirs(os.path.dirname(self._storage_path), exist_ok=True)
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump([asdict(r) for r in self._records], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save long-term memory: {e}")

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculates the cosine similarity between two vectors."""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        return dot_product / (magnitude1 * magnitude2)

    def add_memory(self, memory_id: str, content: str, metadata: Dict[str, Any]) -> None:
        """
        Embeds and stores a new memory record.

        Args:
            memory_id: Unique identifier for the memory.
            content: The text content to remember (e.g., 'Fixed bug by updating JWT header').
            metadata: Contextual data (tags, author, date).
        """
        vector = self._engine.generate_embedding(content)
        record = MemoryRecord(id=memory_id, content=content, vector=vector, metadata=metadata)
        self._records.append(record)
        self._save_memory()
        logger.info(f"Added memory: {memory_id}")

    def search(self, query: str, top_k: int = 3, threshold: float = 0.7) -> List[MemoryRecord]:
        """
        Finds the most semantically relevant memories to a given query.

        Args:
            query: The search string.
            top_k: Maximum number of results to return.
            threshold: Minimum similarity score (0.0 to 1.0).

        Returns:
            List of matching MemoryRecord objects.
        """
        query_vector = self._engine.generate_embedding(query)
        
        scored_records = []
        for record in self._records:
            score = self._cosine_similarity(query_vector, record.vector)
            if score >= threshold:
                scored_records.append((score, record))
                
        # Sort by highest score first
        scored_records.sort(key=lambda x: x[0], reverse=True)
        return [record for score, record in scored_records[:top_k]]

    def iter_memories(self) -> Generator[MemoryRecord, None, None]:
        """Memory-efficient generator for iterating over all records."""
        for record in self._records:
            yield record

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ltm = LongTermMemory("data/test_memory.json")
    ltm.add_memory("playbook-1", "Always use PyJWT instead of jwt library for token validation.", {"tags": ["auth", "security"]})
    
    results = ltm.search("How should I validate tokens?")
    for res in results:
        print(f"Found related memory: {res.content} (Metadata: {res.metadata})")