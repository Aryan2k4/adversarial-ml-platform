"""Evidence-based ATLAS mapping; see docs/EVALUATION.md for sources and scope."""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.services import contracts

logger = get_logger(__name__)

# Stand-in for M3's atlas_catalogue.json. Deliberately tiny — M1 does not own this data.
CATALOGUE: dict[str, dict[str, str]] = {
    "fgsm": {
        "atlas_tactic": "AML.TA0011",
        "atlas_technique": "AML.T0015",
        "mitigation": "Apply adversarial training with FGSM-generated examples; enforce input-norm bounds at inference.",
        "owasp_ml_top10": "ML01: Input Manipulation Attack",
        "nist_ai_rmf": "MEASURE 2.7",
    },
    "pgd": {
        "atlas_tactic": "AML.TA0011",
        "atlas_technique": "AML.T0015",
        "mitigation": "Apply adversarial training with PGD-generated examples; add input-norm bounds checking.",
        "owasp_ml_top10": "ML01: Input Manipulation Attack",
        "nist_ai_rmf": "MEASURE 2.7",
    },
    "random_search": {
        "atlas_tactic": "AML.TA0011",
        "atlas_technique": "AML.T0015",
        "mitigation": "Monitor repeated inference queries and apply rate limits; evaluate adversarial training. Decision-only attacks do not require confidence scores.",
        "owasp_ml_top10": "ML01: Input Manipulation Attack",
        "nist_ai_rmf": "MEASURE 2.8",
    },
    "poisoning": {
        "atlas_tactic": "AML.TA0003",
        "atlas_technique": "AML.T0020",
        "mitigation": "Validate and provenance-track training data; use robust loss / data sanitisation before retraining.",
        "owasp_ml_top10": "ML02: Data Poisoning Attack",
        "nist_ai_rmf": "MANAGE 2.2",
    },
}


def get_findings(raw_results: dict[str, Any], score: dict[str, Any]) -> dict[str, Any]:
    """Contract #4 + #5 in, contract #6 out."""
    logger.info("atlas get_findings", extra={"scan_id": raw_results["scan_id"]})
    findings: list[dict[str, Any]] = []

    for attack, block in raw_results.get("evasion", {}).items():
        findings.append(_finding(attack, {"asr": block.get("asr")}, block.get("asr", 0.0)))
    for attack, block in raw_results.get("black_box", {}).items():
        findings.append(_finding(attack, {"asr": block.get("asr")}, block.get("asr", 0.0)))
    if raw_results.get("poisoning"):
        worst = max(raw_results["poisoning"].values(), key=lambda b: b.get("accuracy_drop", 0.0))
        findings.append(_finding("poisoning", worst, worst.get("accuracy_drop", 0.0)))

    findings = [f for f in findings if (f["evidence"].get("asr", f["evidence"].get("accuracy_drop", 0)) or 0) > 0]
    payload = {"scan_id": raw_results["scan_id"], "findings": findings}
    contracts.assert_findings_shape(payload)
    return payload


def _finding(attack: str, evidence: dict[str, Any], magnitude: float) -> dict[str, Any]:
    entry = CATALOGUE[attack]
    return {"attack": attack, "severity": severity_for(magnitude), "evidence": evidence, **entry}


def severity_for(magnitude: float) -> str:
    """M3 owns the real thresholds from Milestone 2 onward; these are the documented v1 ones."""
    if magnitude >= 0.6:
        return "high"
    if magnitude >= 0.3:
        return "medium"
    return "low"
