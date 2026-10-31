"""Small, dependency-free helpers and configuration for the Governance Agent.

Deliberately self-contained (no import from workflow_agent) so this package
can be evolved, tested, or replaced independently, per the project's
modularity rules. The small amount of duplication with workflow_agent/
(env loading, JSON helpers) is intentional.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# --- Paths ---------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
POLICIES_DIR = PROJECT_ROOT / "policies"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
GOVERNANCE_OUTPUT_DIR = OUTPUTS_DIR / "governance"
RETRIEVED_OUTPUT_DIR = OUTPUTS_DIR / "retrieved"

# --- Anthropic API ---------------------------------------------------------
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
GOVERNANCE_AGENT_MODEL = os.getenv("GOVERNANCE_AGENT_MODEL", DEFAULT_MODEL)
DEFAULT_MAX_TOKENS = int(os.getenv("ANTHROPIC_MAX_TOKENS", "1024"))

# --- Retrieval ---------------------------------------------------------
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))


def ensure_output_dirs() -> None:
    """Create the outputs/ directories this package writes to."""
    for directory in (GOVERNANCE_OUTPUT_DIR, RETRIEVED_OUTPUT_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def save_json(data: Any, path: Path) -> None:
    """Write `data` (a dict/list or a Pydantic model) as pretty JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(data, "model_dump"):
        data = data.model_dump()
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


def extract_json_object(text: str) -> dict:
    """Extract the first top-level JSON object from an LLM text response.

    Handles responses that may be wrapped in markdown code fences.
    """
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found in model response.")
    return json.loads(candidate[start : end + 1])
