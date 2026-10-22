import json
import time
from uuid import uuid4

import numpy as np
import pytest
from pydantic import ValidationError

from app.services.evaluator import Bundle, run, gradient, probabilities
from app.services.contracts import build_job_config
from app.services.sandbox_client import score_results
from app.schemas.scan import ScanCreateRequest


def fixture_bundle():
    # Known decision boundary x=0.5. All four examples initially correct.
    return {"weights": [[-4, 4]], "bias": [2, -2],
            "X_test": [[0.1], [0.49], [0.51], [0.9]], "y_test": [0, 0, 1, 1],
            "X_train": [[0.05], [0.2], [0.8], [0.95]], "y_train": [0, 0, 1, 1]}


def job(tmp_path, attacks=None, params=None, bundle=None):
    path = tmp_path / "model.json"
    path.write_text(json.dumps(bundle or fixture_bundle()))
    return build_job_config(scan_id=uuid4(), model_path=str(path), model_type="linear_json",
                            threat_model="white_box", attacks=attacks or ["fgsm"], params=params or {})


def test_fgsm_matches_known_boundary_and_linf_budget(tmp_path):
    raw = run(job(tmp_path))
    block = raw["evasion"]["fgsm"]
    assert raw["clean_accuracy"] == 1
    assert block["asr"] == 0.5
    assert block["adversarial_accuracy"] == 0.5
    assert block["success_count"] == 2
    assert block["max_perturbation_linf"] <= 0.05 + 1e-12
    assert score_results(raw)["final_score_0_100"] == 50
    assert score_results(raw)["weights"] == {"evasion": 1.0}


def test_analytic_gradient_matches_finite_difference():
    x = np.array([[0.3, 0.7]])
    w = np.array([[1., -2.], [0.2, 0.8]])
    b = np.array([0.1, -0.1]); y = np.array([1])
    analytic = gradient(x, y, w, b)[0]
    numeric = []
    for i in range(2):
        plus, minus = x.copy(), x.copy()
        plus[0, i] += 1e-6; minus[0, i] -= 1e-6
        numeric.append((-np.log(probabilities(plus, w, b)[0, 1]) + np.log(probabilities(minus, w, b)[0, 1])) / 2e-6)
    np.testing.assert_allclose(analytic, numeric, atol=1e-7)


@pytest.mark.parametrize("attack", ["fgsm", "pgd", "random_search"])
def test_zero_epsilon_has_no_effect(tmp_path, attack):
    raw = run(job(tmp_path, [attack], {attack: {"epsilon": 0}}))
    block = raw.get("evasion", raw.get("black_box"))[attack]
    assert block["asr"] == 0
    assert block["max_perturbation_linf"] == 0


def test_pgd_reproducible_and_projected(tmp_path):
    cfg = job(tmp_path, ["pgd"])
    first = run(cfg)
    cfg["scan_id"] = str(uuid4())
    second = run(cfg)
    assert first["evasion"] == second["evasion"]
    assert first["evasion"]["pgd"]["max_perturbation_linf"] <= 0.05 + 1e-12


def test_blackbox_query_accounting(tmp_path):
    block = run(job(tmp_path, ["random_search"], {"random_search": {"query_budget": 3}}))["black_box"]["random_search"]
    assert block["queries_used"] <= 12
    assert block["maximum_queries"] == 12


def test_poisoning_uses_clean_retraining_control(tmp_path):
    raw = run(job(tmp_path, ["poisoning"], {"poisoning": {"contamination_pct": [0, 50]}}))
    zero, half = raw["poisoning"].values()
    assert zero["accuracy_drop"] == 0
    assert zero["f1_drop"] == 0
    assert half["poisoned_count"] == 2
    assert half["accuracy_drop"] == max(0, half["baseline_accuracy"] - half["poisoned_accuracy"])


def test_asr_denominator_excludes_initial_errors(tmp_path):
    bundle = fixture_bundle(); bundle["y_test"][0] = 1
    raw = run(job(tmp_path, bundle=bundle))
    assert raw["eligible_count"] == 3
    assert raw["evasion"]["fgsm"]["asr"] == pytest.approx(2/3)


def test_no_correct_samples_cannot_earn_a_grade(tmp_path):
    bundle = fixture_bundle(); bundle["y_test"] = [1, 1, 0, 0]
    with pytest.raises(ValueError, match="No correctly"):
        run(job(tmp_path, bundle=bundle))


@pytest.mark.parametrize("change", [
    {"weights": [[1]]}, {"y_test": [0]}, {"y_test": [0, 0, 1, 9]},
    {"X_test": [[-1], [2]]}, {"bias": [float("nan"), 0]},
    {"format": "pickle"}, {"code": "print('execute')"},
    {"X_train": [[0.1], [0.2], [0.8], [0.95]]},
])
def test_bundle_validation(change):
    with pytest.raises(ValidationError):
        Bundle.model_validate({**fixture_bundle(), **change})


@pytest.mark.parametrize("payload", [
    {"attacks": ["fgsm", "fgsm"]}, {"attacks": ["hopskipjump"]},
    {"threat_model": "black_box", "attacks": ["fgsm"]},
    {"params": {"fgsm": {"epsilon": -1}}},
    {"params": {"fgsm": {"epsilon": 2}}},
    {"params": {"fgsm": {"shell": "echo bad"}}},
    {"attacks": ["pgd"], "params": {"pgd": {"iterations": 999999}}},
    {"attacks": ["poisoning"], "params": {"poisoning": {"contamination_pct": [51]}}},
])
def test_scan_validation(payload):
    with pytest.raises(ValidationError):
        ScanCreateRequest.model_validate({"model_id": uuid4(), **payload})


def test_subprocess_timeout_terminates(tmp_path, monkeypatch):
    from app.services import sandbox_client
    monkeypatch.setattr(sandbox_client.settings, "SCAN_TIMEOUT_SECONDS", 0.001)
    started = time.monotonic()
    with pytest.raises(RuntimeError, match="terminated"):
        sandbox_client.run_scan(job(tmp_path))
    assert time.monotonic() - started < 3


def test_no_results_cannot_be_graded():
    with pytest.raises(ValueError):
        score_results({"scan_id": "none", "clean_accuracy": 1})


def test_zero_success_is_not_a_vulnerability(tmp_path):
    from app.services.atlas_client import get_findings
    raw = run(job(tmp_path, params={"fgsm": {"epsilon": 0}}))
    assert get_findings(raw, score_results(raw))["findings"] == []
