"""Loads governance policy JSON documents and flattens them into retrievable
clauses.

This module treats the JSON files under policies/ as the only source of
governance truth: it does not add, infer, or embellish any regulation text.
It only restructures the existing nested JSON into flat (policy_id, title,
text) units suitable for keyword/TF-IDF retrieval (see governance_agent/rag.py).
"""
from __future__ import annotations

import itertools
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, List, Tuple

# Bibliographic / non-normative keys that contain no governance rules and
# should not be surfaced as retrievable clauses.
_SKIP_KEYS = {
    "document_metadata",
    "table_of_contents",
    "summary_of_updates",
    "foreword",
    "acknowledgements",
    "page_range",
}

# A bare section number such as "2", "3a", "2.1", "3.24".
_SECTION_ID_RE = re.compile(r"^\d+[a-z]?(\.\d+)*$")
# A section-numbered key with a descriptive suffix, e.g. "2.3_objectives".
_SECTION_PREFIX_RE = re.compile(r"^(\d+[a-z]?(?:\.\d+)*)_")

# Best-effort title/body field names used to describe a heterogeneous dict
# item (e.g. {"principle": ..., "description": ...}) as a single clause.
_TITLE_KEYS = ("principle", "area", "name", "practice", "title", "term", "company", "stage")
_TEXT_KEYS = ("description", "summary", "reason", "content")


@dataclass
class PolicyClause:
    """A single retrievable unit of governance policy text."""

    policy_id: str
    title: str
    text: str
    source_file: str
    clause_type: str = "paragraph"  # paragraph | definition | list_item | example

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "title": self.title,
            "text": self.text,
            "source_file": self.source_file,
            "clause_type": self.clause_type,
        }


def _humanize(key: str) -> str:
    """Turn a JSON key like '3c_operations_management' into a readable title."""
    parts = key.split("_", 1)
    remainder = parts[1] if len(parts) > 1 and any(ch.isdigit() for ch in parts[0]) else key
    return remainder.replace("_", " ").strip().title()


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "clause"


def _dict_item_summary(item: dict) -> Tuple[str, str]:
    """Best-effort (title, text) extraction from a heterogeneous dict item."""
    title = next((item[k] for k in _TITLE_KEYS if isinstance(item.get(k), str)), None)
    text_fragments = [item[k] for k in _TEXT_KEYS if isinstance(item.get(k), str)]
    if not text_fragments:
        text_fragments = [str(v) for v in item.values() if isinstance(v, str) and v != title]
    text = " ".join(text_fragments) if text_fragments else json.dumps(item, ensure_ascii=False)
    return title or "Untitled", text


def _make_id(key: str, path: List[str], counter: Iterator[int]) -> str:
    """Derive a readable, de-duplicated policy_id for a given JSON key."""
    if _SECTION_ID_RE.match(key):
        return f"IMDA-{key}"
    prefix_match = _SECTION_PREFIX_RE.match(key)
    if prefix_match:
        return f"IMDA-{prefix_match.group(1)}"
    breadcrumb = _slugify(path[-1]) if path else "root"
    return f"IMDA-{breadcrumb}-{next(counter)}"


def _flatten_list(
    key: str,
    items: list,
    path: List[str],
    source_file: str,
    counter: Iterator[int],
    clauses: List[PolicyClause],
) -> None:
    base_id = _make_id(key, path, counter)
    title = " > ".join(path + [_humanize(key)]) if path else _humanize(key)
    for index, item in enumerate(items, start=1):
        if isinstance(item, str):
            clauses.append(PolicyClause(f"{base_id}-{index}", title, item, source_file, "list_item"))
        elif isinstance(item, dict):
            item_title, item_text = _dict_item_summary(item)
            clause_type = "example" if "company" in item else "list_item"
            clauses.append(
                PolicyClause(f"{base_id}-{index}", f"{title} \u2014 {item_title}", item_text, source_file, clause_type)
            )
        # Nested lists or other scalar list items carry no retrievable text.


def _flatten(
    node: Any,
    path: List[str],
    source_file: str,
    counter: Iterator[int],
    clauses: List[PolicyClause],
) -> None:
    if not isinstance(node, dict):
        return
    for key, value in node.items():
        if key in _SKIP_KEYS:
            continue
        if isinstance(value, str):
            clause_id = _make_id(key, path, counter)
            title = " > ".join(path + [_humanize(key)]) if path else _humanize(key)
            clause_type = "definition" if path and path[-1].lower() == "terms" else "paragraph"
            clauses.append(PolicyClause(clause_id, title, value, source_file, clause_type))
        elif isinstance(value, list):
            _flatten_list(key, value, path, source_file, counter, clauses)
        elif isinstance(value, dict):
            _flatten(value, path + [_humanize(key)], source_file, counter, clauses)
        # Numbers, booleans, and None carry no retrievable policy text.


def flatten_policy_document(document: dict, source_file: str) -> List[PolicyClause]:
    """Flatten one parsed policy JSON document into a list of PolicyClause."""
    clauses: List[PolicyClause] = []
    counter = itertools.count(1)
    _flatten(document, [], source_file, counter, clauses)
    return clauses


def load_policy_clauses(policies_dir: Path) -> List[PolicyClause]:
    """Load and flatten every *.json policy file found in `policies_dir`."""
    clauses: List[PolicyClause] = []
    for path in sorted(Path(policies_dir).glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            document = json.load(handle)
        clauses.extend(flatten_policy_document(document, path.name))
    return clauses
