"""Lightweight TF-IDF retrieval over workflow context and templates.

No embeddings or vector databases are used, per project constraints. The
retrieval interface (`retrieve_workflow_context`) is deliberately narrow so
it can later be swapped for an embedding-based implementation without
touching callers.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Optional

from workflow_agent import config
from workflow_agent.utils import read_csv_rows


@dataclass
class RetrievedChunk:
    """A single retrieved piece of workflow context."""

    chunk_id: str
    source: str
    content: str
    score: float

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "source": self.source,
            "content": self.content,
            "score": round(self.score, 4),
        }


def _tokenize(text: str) -> List[str]:
    """Small, language-agnostic tokenizer (lowercased word/CJK runs)."""
    return re.findall(r"[a-zA-Z0-9]+|[\u4e00-\u9fff]|[\u3040-\u30ff]+", text.lower())


class TfidfRetriever:
    """Minimal TF-IDF retriever over an in-memory document list.

    Kept dependency-free (no sklearn/numpy) so it is trivial to read, test,
    and later replace with an embedding-based retriever behind the same
    `retrieve()` interface.
    """

    def __init__(self, documents: List[dict]):
        """`documents` is a list of {"id", "source", "content"} dicts."""
        self._documents = documents
        self._tokenized = [_tokenize(doc["content"]) for doc in documents]
        self._doc_freq = self._build_doc_freq(self._tokenized)
        self._num_docs = len(documents)

    @staticmethod
    def _build_doc_freq(tokenized_docs: List[List[str]]) -> Counter:
        doc_freq: Counter = Counter()
        for tokens in tokenized_docs:
            doc_freq.update(set(tokens))
        return doc_freq

    def _idf(self, term: str) -> float:
        df = self._doc_freq.get(term, 0)
        return math.log((self._num_docs + 1) / (df + 1)) + 1.0

    def _vector(self, tokens: List[str]) -> dict:
        counts = Counter(tokens)
        total = sum(counts.values()) or 1
        return {term: (count / total) * self._idf(term) for term, count in counts.items()}

    @staticmethod
    def _cosine(vec_a: dict, vec_b: dict) -> float:
        shared = set(vec_a) & set(vec_b)
        numerator = sum(vec_a[t] * vec_b[t] for t in shared)
        norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
        norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return numerator / (norm_a * norm_b)

    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedChunk]:
        query_vector = self._vector(_tokenize(query))
        scored = []
        for doc, tokens in zip(self._documents, self._tokenized):
            score = self._cosine(query_vector, self._vector(tokens))
            if score > 0:
                scored.append((score, doc))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [
            RetrievedChunk(chunk_id=doc["id"], source=doc["source"], content=doc["content"], score=score)
            for score, doc in scored[:top_k]
        ]


def _load_documents() -> List[dict]:
    documents = []
    for row in read_csv_rows(config.WORKFLOW_CONTEXT_CSV):
        documents.append(
            {
                "id": row.get("context_id", "UNKNOWN"),
                "source": "workflow_context.csv",
                "content": f"{row.get('keywords', '')} {row.get('content', '')}".strip(),
            }
        )
    for row in read_csv_rows(config.WORKFLOW_TEMPLATES_CSV):
        content = (
            f"{row.get('request_type', '')}: {row.get('example_business_goal', '')} "
            f"capabilities: {row.get('example_capabilities', '')} notes: {row.get('notes', '')}"
        )
        documents.append(
            {
                "id": row.get("template_id", "UNKNOWN"),
                "source": "workflow_templates.csv",
                "content": content,
            }
        )
    return documents


@lru_cache(maxsize=1)
def build_retriever() -> TfidfRetriever:
    """Build (and cache) a retriever over the current workflow/ CSVs."""
    return TfidfRetriever(_load_documents())


def retrieve_workflow_context(query: str, top_k: Optional[int] = None) -> List[RetrievedChunk]:
    """Retrieve the most relevant workflow context/template snippets for a query."""
    retriever = build_retriever()
    return retriever.retrieve(query, top_k or config.RETRIEVAL_TOP_K)
