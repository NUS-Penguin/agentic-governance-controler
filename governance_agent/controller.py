"""Sequential orchestration for the Governance Agent stage of the pipeline.

Retrieval -> Reasoning -> Governance Decision. This module receives only
plain, JSON-serialisable data (a structured workflow dict and a list of
upstream context dicts) so it never depends on workflow_agent's Python
classes — the two agent packages remain independently replaceable.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from governance_agent import prompts, utils
from governance_agent.client import call_claude
from governance_agent.models import GovernanceDecision
from governance_agent.policy_loader import PolicyClause
from governance_agent.rag import retrieve_policy_clauses


def _format_workflow_context(workflow_context: List[Dict[str, Any]]) -> str:
    if not workflow_context:
        return "(no upstream workflow context available)"
    return "\n".join(f"- [{chunk.get('source')}:{chunk.get('chunk_id')}] {chunk.get('content')}" for chunk in workflow_context)


def _format_policy_context(clauses: List[PolicyClause]) -> str:
    if not clauses:
        return "(no relevant policy excerpts retrieved)"
    return "\n".join(f"- [{clause.policy_id}] {clause.title}: {clause.text}" for clause in clauses)


def _workflow_to_query(workflow_payload: Dict[str, Any]) -> str:
    """Build a retrieval query string from the structured workflow fields."""
    parts = [
        workflow_payload.get("request_type") or "",
        workflow_payload.get("business_goal") or "",
        " ".join(workflow_payload.get("requested_capabilities") or []),
        " ".join(workflow_payload.get("affected_systems") or []),
        " ".join(workflow_payload.get("external_services") or []),
        workflow_payload.get("deployment_environment") or "",
        workflow_payload.get("automation_level") or "",
        "human review removed" if workflow_payload.get("human_review_removed") else "",
        " ".join(workflow_payload.get("new_permissions") or []),
    ]
    return " ".join(part for part in parts if part)


def evaluate_workflow(
    workflow_payload: Dict[str, Any],
    workflow_context: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[GovernanceDecision, List[PolicyClause]]:
    """Retrieve relevant policy clauses and produce a GovernanceDecision."""
    workflow_context = workflow_context or []
    query_text = _workflow_to_query(workflow_payload)
    clauses = retrieve_policy_clauses(query_text)

    user_prompt = prompts.USER_PROMPT_TEMPLATE.format(
        workflow_json=json.dumps(workflow_payload, indent=2, ensure_ascii=False),
        workflow_context=_format_workflow_context(workflow_context),
        policy_context=_format_policy_context(clauses),
    )
    raw_response = call_claude(system_prompt=prompts.SYSTEM_PROMPT, user_prompt=user_prompt)
    payload = utils.extract_json_object(raw_response)
    decision = GovernanceDecision.model_validate(payload)
    return decision, clauses


def run_governance_agent(
    request_id: str,
    workflow_payload: Dict[str, Any],
    workflow_context: Optional[List[Dict[str, Any]]] = None,
) -> GovernanceDecision:
    """Run the Governance Agent end-to-end for one request and save outputs."""
    decision, clauses = evaluate_workflow(workflow_payload, workflow_context)

    utils.save_json(
        [clause.to_dict() for clause in clauses],
        utils.RETRIEVED_OUTPUT_DIR / f"{request_id}_policy_context.json",
    )
    utils.save_json(decision, utils.GOVERNANCE_OUTPUT_DIR / f"{request_id}.json")

    return decision
