"""Command-line entry point for the enterprise workflow simulation.

Runs the Workflow Agent followed automatically by the Governance Agent for
either a single ad-hoc request or a batch of cases from
workflow/workflow_cases.csv. This is the only module that imports both agent
packages; neither workflow_agent nor governance_agent imports the other.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import List, Optional

from governance_agent import utils as governance_utils
from governance_agent.controller import run_governance_agent
from governance_agent.models import GovernanceDecision
from workflow_agent import config
from workflow_agent.utils import append_log_row, new_request_id, read_csv_rows
from workflow_agent.workflow import WorkflowAgentResult, run_workflow_agent


@dataclass
class SimulationResult:
    """The combined output of running one request through both agents."""

    request_id: str
    workflow_result: WorkflowAgentResult
    governance_decision: GovernanceDecision


def simulate_request(request_text: str, request_id: Optional[str] = None) -> SimulationResult:
    """Run one request through the Workflow Agent then the Governance Agent."""
    request_id = request_id or new_request_id()
    # A fresh run_id is generated for every execution (even re-runs of the
    # same request_id/case), so each simulation attempt has its own
    # unambiguous row group in the shared outputs/logs/run_log.csv audit trail.
    run_id = new_request_id("run")

    append_log_row(config.RUN_LOG_CSV, run_id, request_id, "start", f"Starting simulation for request: {request_text!r}")
    print(f"[{request_id}] Running Workflow Agent...")
    workflow_result = run_workflow_agent(request_id, request_text)
    append_log_row(
        config.RUN_LOG_CSV,
        run_id,
        request_id,
        "workflow_agent_complete",
        "Workflow Agent completed; parsed workflow saved to outputs/parsed/.",
    )

    print(f"[{request_id}] Running Governance Agent...")
    governance_decision = run_governance_agent(
        request_id,
        workflow_result.parsed_workflow.workflow.model_dump(),
        [chunk.to_dict() for chunk in workflow_result.retrieved_context],
    )
    append_log_row(
        config.RUN_LOG_CSV,
        run_id,
        request_id,
        "governance_agent_complete",
        f"approved={governance_decision.approved} "
        f"tier={governance_decision.tier} risk_score={governance_decision.risk_score}",
    )

    print(
        f"[{request_id}] approved={governance_decision.approved} "
        f"tier={governance_decision.tier} risk_score={governance_decision.risk_score}"
    )
    return SimulationResult(request_id, workflow_result, governance_decision)


def simulate_batch() -> List[SimulationResult]:
    """Run every case in workflow/workflow_cases.csv through the pipeline."""
    cases = read_csv_rows(config.WORKFLOW_CASES_CSV)
    if not cases:
        print(f"No cases found in {config.WORKFLOW_CASES_CSV}")
        return []
    results = []
    for row in cases:
        request_text = row.get("request_text", "")
        if not request_text:
            continue
        request_id = row.get("case_id") or new_request_id()
        results.append(simulate_request(request_text, request_id))
    return results


def main() -> None:
    """Parse CLI arguments and run either a single request or the full batch."""
    config.ensure_output_dirs()
    governance_utils.ensure_output_dirs()

    arg_parser = argparse.ArgumentParser(description="Enterprise AI workflow simulation harness.")
    arg_parser.add_argument("--request", type=str, help="Run a single ad-hoc request instead of the batch.")
    arg_parser.add_argument("--request-id", type=str, help="Optional id to use for a single --request run.")
    args = arg_parser.parse_args()

    if args.request:
        simulate_request(args.request, args.request_id)
    else:
        results = simulate_batch()
        print(f"Completed {len(results)} case(s). See outputs/ for details.")


if __name__ == "__main__":
    main()
