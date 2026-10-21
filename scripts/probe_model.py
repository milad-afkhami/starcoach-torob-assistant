"""Explicit local smoke check; reads credential paths, never prints credentials."""

import os
import time
from pathlib import Path
from torob.codex_cli import CodexCliClient
from torob.model_types import ModelRequest

schema = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["HOLD"]},
        "evidence_ids": {"type": "array", "items": {"enum": ["fixture-1"]}},
        "reason_fa": {"type": "string"},
    },
    "required": ["action", "evidence_ids", "reason_fa"],
    "additionalProperties": False,
}
client = CodexCliClient(
    binary=Path(os.environ["CODEX_BINARY_PATH"]),
    auth_file=Path(os.environ["CODEX_AUTH_FILE"]),
    image=os.environ["CODEX_IMAGE"],
    gate_dir=Path(f"/tmp/starcoach-codex-{os.getuid()}"),
)
request = ModelRequest(
    id="readiness-probe",
    schema_id="probe",
    schema_version="1",
    prompt_version="1",
    evidence_ids=["fixture-1"],
    payload={"fixture-1": "No current quote or verified account. A brief Persian reason is required."},
    deadline_utc=time.time() + 60,
)
result = client.generate(request, schema)
print(result.model_dump_json(indent=2))
