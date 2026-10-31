"""Thin wrapper around the Anthropic Python SDK for the Governance Agent.

Kept intentionally separate from workflow_agent/client.py so each agent's
LLM access remains independently configurable and replaceable.

If no real ANTHROPIC_API_KEY is configured, `call_claude` does not raise or
make a network call: it returns a deterministic default stub response
matching the GovernanceDecision schema (tier UNKNOWN, approved False) so the
rest of the pipeline can still run end-to-end, e.g. for smoke testing
without API access.
"""
from __future__ import annotations

import json
from typing import Optional

import anthropic

from governance_agent import utils

_NO_API_KEY_NOTICE = (
    "ANTHROPIC_API_KEY is not configured; returning a default stub response instead of calling Claude."
)

# A schema-valid, non-hallucinated default GovernanceDecision used only when
# no real API key is available. No policy is flagged and no approval is
# granted, since no actual evaluation took place.
_DEFAULT_RESPONSE = json.dumps(
    {
        "approved": False,
        "tier": "UNKNOWN",
        "risk_score": 0,
        "summary": _NO_API_KEY_NOTICE,
        "decision": "Governance review could not be performed: no API key configured.",
        "flagged_policies": [],
        "supporting_evidence": [],
    }
)


def has_valid_api_key() -> bool:
    """Whether a real (non-placeholder) ANTHROPIC_API_KEY is configured."""
    return bool(utils.ANTHROPIC_API_KEY) and utils.ANTHROPIC_API_KEY != "your_api_key_here"


def get_client() -> anthropic.Anthropic:
    """Build an Anthropic client using the configured API key."""
    if not has_valid_api_key():
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add a real key to .env before running the Governance Agent."
        )
    return anthropic.Anthropic(api_key=utils.ANTHROPIC_API_KEY)


def call_claude(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """Send a single-turn prompt to Claude and return the raw text response.

    Returns a default stub response (see `_DEFAULT_RESPONSE`) without making
    a network call if no real API key is configured.

    Note: sampling parameters (temperature/top_p/top_k) are intentionally
    not exposed here — the Messages API no longer accepts them.
    """
    if not has_valid_api_key():
        print(f"[governance_agent.client] WARNING: {_NO_API_KEY_NOTICE}")
        return _DEFAULT_RESPONSE

    client = get_client()
    response = client.messages.create(
        model=model or utils.GOVERNANCE_AGENT_MODEL,
        max_tokens=max_tokens or utils.DEFAULT_MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")
