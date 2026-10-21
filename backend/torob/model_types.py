from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class ModelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=100)
    schema_id: str = Field(min_length=1, max_length=100)
    schema_version: str
    prompt_version: str
    evidence_ids: list[str]
    payload: dict[str, Any]
    deadline_utc: float = Field(allow_inf_nan=False)


class ModelResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str
    provider: str
    model: str
    cli_version: str
    elapsed_ms: int
    value: dict[str, Any]
