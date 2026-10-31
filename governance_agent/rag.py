"""Lightweight TF-IDF retrieval over governance policy clauses.

No embeddings or vector databases are used, per project constraints. This
module is self-contained (no shared code with workflow_agent/rag.py) so it
can evolve or be replaced independently of the Workflow Agent.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from functools import lru_cache
from typing import List, Optional

from governance_agent import utils
from governance_agent.policy_loader import PolicyClause, load_policy_clauses


def _tokenize(text: str) -> List[str]:
    """Small, language-agnostic tokenizer (lowercased word/CJK runs)."""
    return re.findall(r"[a-zA-Z0-9]+|[\u4e00-\u9fff]|[\u3040-\u30ff]+", text.lower())


class PolicyTfidfRetriever:
    """Minimal TF-IDF retriever over the flattened policy clause corpus."""

    def __init__(self, clauses: List[PolicyClause]):
        self._clauses = clauses
        self._tokenized = [_tokenize(f"{clause.title} {clause.text}") for clause in clauses]
        self._doc_freq = self._build_doc_freq(self._tokenized)
        self._num_docs = len(clauses)

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

    def retrieve(self, query: str, top_k: int) -> List[PolicyClause]:
        query_vector = self._vector(_tokenize(query))
        scored = []
        for clause, tokens in zip(self._clauses, self._tokenized):
            score = self._cosine(query_vector, self._vector(tokens))
            if score > 0:
                scored.append((score, clause))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [clause for _, clause in scored[:top_k]]


@lru_cache(maxsize=1)
def _build_retriever() -> PolicyTfidfRetriever:
    return PolicyTfidfRetriever(load_policy_clauses(utils.POLICIES_DIR))


def retrieve_policy_clauses(query: str, top_k: Optional[int] = None) -> List[PolicyClause]:
    """Retrieve the most relevant policy clauses for a governance query."""
    retriever = _build_retriever()
    return retriever.retrieve(query, top_k or utils.RETRIEVAL_TOP_K)
