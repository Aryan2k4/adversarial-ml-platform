"""Request/response shapes for scans. The nested contract objects mirror
ARCHITECTURE.md contracts #3-#6 exactly — do not add fields here without editing that file."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

ThreatModel = Literal["white_box", "black_box"]
AttackName = Literal["fgsm", "pgd", "random_search", "poisoning"]
ScanStatus = Literal["queued", "running", "done", "failed"]
Severity = Literal["low", "medium", "high", "critical"]


class ScanCreateRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: UUID
    threat_model: ThreatModel = "white_box"
    attacks: list[AttackName] = Field(default_factory=lambda: ["fgsm"], min_length=1, max_length=4)
    seed: int = Field(default=42, ge=0, le=4294967295)
    # free-form per-attack params; shape is contract #3's "params" block
    params: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_attack_params(self):
        from app.services.contracts import _with_default_params
        if len(set(self.attacks)) != len(self.attacks):
            raise ValueError("attacks must be unique")
        if self.threat_model == "black_box" and any(a != "random_search" for a in self.attacks):
            raise ValueError("black_box permits only random_search")
        if set(self.params) - set(self.attacks):
            raise ValueError("params may only contain selected attacks")
        schemas = {"fgsm": FGSMParams, "pgd": PGDParams, "random_search": SearchParams, "poisoning": PoisonParams}
        self.params = {k: schemas[k].model_validate(v).model_dump() for k, v in _with_default_params(self.attacks, self.params).items()}
        return self


class FGSMParams(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    epsilon: float = Field(default=0.05, ge=0, le=1)


class PGDParams(FGSMParams):
    step_size: float = Field(default=0.01, gt=0, le=1)
    iterations: int = Field(default=40, ge=1, le=200)


class SearchParams(FGSMParams):
    query_budget: int = Field(default=100, ge=1, le=2000)


class PoisonParams(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    contamination_pct: list[float] = Field(default_factory=lambda: [1, 5, 10], min_length=1, max_length=5)
    method: Literal["label_flip"] = "label_flip"

    @model_validator(mode="after")
    def bounds(self):
        if any(not 0 <= p <= 50 for p in self.contamination_pct):
            raise ValueError("contamination percentages must be between 0 and 50")
        if len(set(self.contamination_pct)) != len(self.contamination_pct):
            raise ValueError("contamination percentages must be unique")
        return self


class ScoreResponse(BaseModel):
    """Contract #5."""

    model_config = ConfigDict(from_attributes=True)

    component_scores: dict[str, float]
    weights: dict[str, float]
    final_score_0_100: float = Field(..., ge=0, le=100)
    grade: Literal["A", "B", "C", "D", "F"]


class FindingResponse(BaseModel):
    """Contract #6, one entry."""

    model_config = ConfigDict(from_attributes=True)

    attack: str
    atlas_tactic: str
    atlas_technique: str
    severity: Severity
    evidence: dict[str, Any] = Field(default_factory=dict)
    mitigation: str
    owasp_ml_top10: str | None = None
    nist_ai_rmf: str | None = None


class ScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID
    model_id: UUID
    status: ScanStatus
    threat_model: ThreatModel
    attack_config: dict[str, Any]
    created_at: datetime
    completed_at: datetime | None = None
    error: str | None = None
    # populated only once status == "done"
    score: ScoreResponse | None = None
    findings: list[FindingResponse] = Field(default_factory=list)
    raw_results: dict[str, Any] | None = Field(
        None, description="contract #4 blob, verbatim as produced by the attack engine"
    )


class ScanSummary(BaseModel):
    """Row shape for GET /models/{id}/scans (score-history trend view)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: ScanStatus
    created_at: datetime
    final_score: float | None = None
    grade: str | None = None
