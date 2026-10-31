"""Centralised configuration for the Workflow Agent.

Loads environment variables from .env and exposes the paths and model
settings this package needs. Kept separate from governance_agent's own
configuration (see governance_agent/utils.py) so each agent package stays
independently configurable and replaceable.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- Paths ---------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = PROJECT_ROOT / "workflow"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
PARSED_OUTPUT_DIR = OUTPUTS_DIR / "parsed"
RETRIEVED_OUTPUT_DIR = OUTPUTS_DIR / "retrieved"
LOGS_OUTPUT_DIR = OUTPUTS_DIR / "logs"
RUN_LOG_CSV = LOGS_OUTPUT_DIR / "run_log.csv"

WORKFLOW_CASES_CSV = WORKFLOW_DIR / "workflow_cases.csv"
WORKFLOW_CONTEXT_CSV = WORKFLOW_DIR / "workflow_context.csv"
WORKFLOW_TEMPLATES_CSV = WORKFLOW_DIR / "workflow_templates.csv"
SAMPLE_REQUESTS_CSV = WORKFLOW_DIR / "sample_requests.csv"

# --- Anthropic API ---------------------------------------------------------
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
WORKFLOW_AGENT_MODEL = os.getenv("WORKFLOW_AGENT_MODEL", DEFAULT_MODEL)
DEFAULT_MAX_TOKENS = int(os.getenv("ANTHROPIC_MAX_TOKENS", "1024"))

# --- Retrieval ---------------------------------------------------------
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))


def ensure_output_dirs() -> None:
    """Create the outputs/ directory tree if it does not already exist."""
    for directory in (PARSED_OUTPUT_DIR, RETRIEVED_OUTPUT_DIR, LOGS_OUTPUT_DIR):
        directory.mkdir(parents=True, exist_ok=True)
