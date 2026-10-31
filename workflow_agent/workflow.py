"""Sequential orchestration for the Workflow Agent stage of the pipeline.

Natural Language -> Retrieval -> Structured Workflow Object. This module
contains no governance logic; it only coordinates the Workflow Agent's own
steps and persists its intermediate outputs for transparency.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from workflow_agent import config
from workflow_agent.models import ParsedWorkflow
from workflow_agent.parser import parse_request
from workflow_agent.rag import RetrievedChunk, retrieve_workflow_context
from workflow_agent.utils import save_json


@dataclass
class WorkflowAgentResult:
    """Everything the Workflow Agent produced for one request."""

    request_id: str
    parsed_workflow: ParsedWorkflow
    retrieved_context: List[RetrievedChunk]


def run_workflow_agent(request_id: str, request_text: str) -> WorkflowAgentResult:
    """Run the Workflow Agent end-to-end for a single request and save outputs."""
    retrieved_context = retrieve_workflow_context(request_text)
    parsed_workflow = parse_request(request_text, retrieved_context)

    save_json(parsed_workflow, config.PARSED_OUTPUT_DIR / f"{request_id}.json")
    save_json(
        [chunk.to_dict() for chunk in retrieved_context],
        config.RETRIEVED_OUTPUT_DIR / f"{request_id}_workflow_context.json",
    )

    return WorkflowAgentResult(
        request_id=request_id,
        parsed_workflow=parsed_workflow,
        retrieved_context=retrieved_context,
    )
