"""Bounded data-only evaluator subprocess and empirical scoring."""
from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from app.core.config import settings
from app.services import contracts


def run_scan(job_config: dict[str, Any]) -> dict[str, Any]:
    env = {k: v for k, v in os.environ.items() if k.upper() in {
        "PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME", "LANG"
    }}
    env.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", PYTHONIOENCODING="utf-8")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "app.services.evaluator"],
            input=json.dumps(job_config), capture_output=True, text=True, encoding="utf-8",
            cwd=Path(__file__).resolve().parents[2], env=env,
            timeout=settings.SCAN_TIMEOUT_SECONDS,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Evaluator exceeded {settings.SCAN_TIMEOUT_SECONDS}s and was terminated") from exc
    if result.returncode:
        raise ValueError(result.stderr.strip()[-500:] or "Evaluator failed")
    raw = json.loads(result.stdout)
    contracts.assert_raw_results_shape(raw)
    return raw


def score_results(raw_results: dict[str, Any]) -> dict[str, Any]:
    """Contract #4 in, contract #5 out.

    The formula below is ARCHITECTURE.md section 5 v1 verbatim, so M2's real engine
    should produce the same numbers for the same input — it just replaces this body.
    """
    components = {
        "evasion": _mean(
            [block.get("asr", 0.0) for block in raw_results.get("evasion", {}).values()]
        ),
        "black_box": _mean(
            [block.get("asr", 0.0) for block in raw_results.get("black_box", {}).values()]
        ),
        "poisoning": _mean(
            [block.get("accuracy_drop", 0.0) for block in raw_results.get("poisoning", {}).values()]
        ),
    }
    base_weights = {"evasion": 0.4, "black_box": 0.3, "poisoning": 0.3}
    components = {k: v for k, v in components.items() if raw_results.get(k)}
    if not components:
        raise ValueError("Cannot grade a scan without evaluated attacks")
    total = sum(base_weights[k] for k in components)
    weights = {k: base_weights[k] / total for k in components}
    badness = sum(weights[k] * components[k] for k in weights)
    final = round(100 - 100 * badness, 1)
    score = {
        "scan_id": raw_results["scan_id"],
        "component_scores": {k: round(v, 3) for k, v in components.items()},
        "weights": weights,
        "final_score_0_100": final,
        "grade": grade_for(final),
    }
    contracts.assert_score_shape(score)
    return score


def grade_for(final_score: float) -> str:
    if final_score >= 90:
        return "A"
    if final_score >= 75:
        return "B"
    if final_score >= 60:
        return "C"
    if final_score >= 40:
        return "D"
    return "F"


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


