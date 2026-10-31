"""Small, dependency-free helper functions shared across the Workflow Agent."""
from __future__ import annotations

import csv
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    """Read a CSV file into a list of plain dict rows. Returns [] if missing."""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def save_json(data: Any, path: Path) -> None:
    """Write `data` (a dict/list or a Pydantic model) as pretty JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(data, "model_dump"):
        data = data.model_dump()
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


def new_request_id(prefix: str = "req") -> str:
    """Generate a short, unique identifier for a simulation run."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def utc_timestamp() -> str:
    """Return a filesystem-safe UTC timestamp, e.g. 20260131T120000Z."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


_LOG_FIELDNAMES = ["run_id", "request_id", "timestamp", "stage", "message"]


def append_log_row(path: Path, run_id: str, request_id: str, stage: str, message: str) -> None:
    """Append one row to the shared run-log CSV, writing the header if new.

    Every call to this function represents a single audit-trail entry for
    one simulation run; `run_id` uniquely identifies that execution even
    when the same `request_id`/case is simulated multiple times.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new_file = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        if is_new_file:
            writer.writerow(_LOG_FIELDNAMES)
        writer.writerow([run_id, request_id, utc_timestamp(), stage, message])


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
