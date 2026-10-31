"""Typed schema for the Governance Agent's structured output."""
from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field

Tier = Literal["GREEN", "YELLOW", "RED", "UNKNOWN"]


class FlaggedPolicy(BaseModel):
    """A single governance policy clause relevant to the decision.

    `policy_id` must reference a clause that was actually retrieved and
    shown to the model; see governance_agent/policy_loader.py.
    """

    policy_id: str
    title: str
    reason: str


class GovernanceDecision(BaseModel):
    """Top-level output of the Governance Agent."""

    approved: bool
    tier: Tier
    risk_score: int = Field(ge=0, le=100)
    summary: str
    decision: str
    flagged_policies: List[FlaggedPolicy] = Field(default_factory=list)
    supporting_evidence: List[str] = Field(default_factory=list)
