"""Natural language -> structured workflow object.

This module owns the single responsibility of turning one customer request
into a validated ParsedWorkflow. It performs no retrieval and no governance
reasoning itself.
"""
from __future__ import annotations

from typing import List

from workflow_agent import prompts
from workflow_agent.client import call_claude
from workflow_agent.models import ParsedWorkflow
from workflow_agent.rag import RetrievedChunk
from workflow_agent.utils import extract_json_object


def _format_context(chunks: List[RetrievedChunk]) -> str:
    if not chunks:
        return "(no relevant context retrieved)"
    return "\n".join(f"- [{chunk.source}:{chunk.chunk_id}] {chunk.content}" for chunk in chunks)


def parse_request(request_text: str, retrieved_context: List[RetrievedChunk]) -> ParsedWorkflow:
    """Parse a raw enterprise request into a structured ParsedWorkflow."""
    user_prompt = prompts.USER_PROMPT_TEMPLATE.format(
        request_text=request_text.strip(),
        retrieved_context=_format_context(retrieved_context),
    )
    raw_response = call_claude(system_prompt=prompts.SYSTEM_PROMPT, user_prompt=user_prompt)
    payload = extract_json_object(raw_response)
    return ParsedWorkflow.model_validate(payload)
