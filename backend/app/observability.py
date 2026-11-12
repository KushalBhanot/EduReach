"""One structured JSON log line per request.

Cloud Run ships stdout to Cloud Logging, which parses JSON lines into
queryable fields (jsonPayload.latency_ms, jsonPayload.cost_usd, ...).
`severity` and the trace key are special fields Cloud Logging understands.
"""

import json
import sys
import time


def trace_field(project: str | None, header: str | None) -> dict:
    """Links the log line to its Cloud Trace trace (header: TRACE_ID/SPAN_ID;o=1)."""
    if not project or not header:
        return {}
    trace_id = header.split("/", 1)[0]
    return {"logging.googleapis.com/trace": f"projects/{project}/traces/{trace_id}"}


def log_event(message: str, severity: str = "INFO", **fields) -> None:
    record = {"severity": severity, "message": message, "time": time.time(), **fields}
    print(json.dumps(record, default=str), file=sys.stdout, flush=True)
