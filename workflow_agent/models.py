"""Typed schema for the Workflow Agent's structured output.

These models intentionally contain no governance fields (no approval, risk,
or compliance concepts) — the Workflow Agent only parses requests into a
normalised schema.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

AutomationLevel = Literal["Manual", "Semi", "Full", "UNKNOWN"]


class WorkflowMetadata(BaseModel):
    """Parser-level metadata describing how confidently the request was understood."""

    languages_detected: List[str] = Field(default_factory=list)
    parser_confidence: float = Field(ge=0.0, le=1.0)
    ambiguities: List[str] = Field(default_factory=list)


class WorkflowObject(BaseModel):
    """The normalised, structured representation of an enterprise request.

    Any field that cannot be confidently extracted from the request is set
    to None (scalar fields), "UNKNOWN" (automation_level), or an empty list
    (list fields) rather than guessed.
    """

    request_type: Optional[str] = None
    business_goal: Optional[str] = None
    requested_capabilities: List[str] = Field(default_factory=list)
    affected_systems: List[str] = Field(default_factory=list)
    affected_departments: List[str] = Field(default_factory=list)
    external_services: List[str] = Field(default_factory=list)
    integrations: List[str] = Field(default_factory=list)
    deployment_environment: Optional[str] = None
    human_review_removed: Optional[bool] = None
    automation_level: AutomationLevel = "UNKNOWN"
    new_permissions: List[str] = Field(default_factory=list)


class ParsedWorkflow(BaseModel):
    """Top-level output of the Workflow Agent."""

    metadata: WorkflowMetadata
    workflow: WorkflowObject
