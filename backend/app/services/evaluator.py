"""Reproducible attacks on data-only linear-softmax model bundles.

No pickle, Python, custom operator or uploaded executable is loaded. All features
are continuous and already scaled to [0, 1]. See docs/EVALUATION.md.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Bundle(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    format: str = "linear-softmax-v1"
    weights: list[list[float]] = Field(min_length=1, max_length=128)
    bias: list[float] = Field(min_length=2, max_length=20)
    X_test: list[list[float]] = Field(min_length=2, max_length=1000)
    y_test: list[int] = Field(min_length=2, max_length=1000)
    X_train: list[list[float]] | None = Field(default=None, min_length=2, max_length=2000)
    y_train: list[int] | None = Field(default=None, min_length=2, max_length=2000)
    description: str = Field(default="User-supplied evaluation dataset", max_length=500)

    @model_validator(mode="after")
    def dimensions(self):
        if self.format != "linear-softmax-v1":
            raise ValueError("format must be linear-softmax-v1")
        features, classes = len(self.weights), len(self.bias)
        if any(len(row) != classes for row in self.weights):
            raise ValueError("weights must have shape [features, classes]")
        if np.max(np.abs(self.weights)) > 10000 or np.max(np.abs(self.bias)) > 10000:
            raise ValueError("model coefficients must be bounded by 10000")
        if (self.X_train is None) != (self.y_train is None):
            raise ValueError("provide both X_train and y_train for poisoning")
        for split in ("test", "train"):
            x, y = getattr(self, f"X_{split}"), getattr(self, f"y_{split}")
            if x is None:
                continue
            if len(x) != len(y) or any(len(row) != features for row in x):
                raise ValueError(f"{split}: mismatched sample or feature dimensions")
            if any(label < 0 or label >= classes for label in y):
                raise ValueError(f"{split}: labels must be class indices 0..{classes - 1}")
            if np.min(x) < 0 or np.max(x) > 1:
                raise ValueError(f"{split}: features must be scaled to [0, 1]")
        if self.X_train is not None:
            train_rows = {tuple(row) for row in self.X_train}
            if any(tuple(row) in train_rows for row in self.X_test):
                raise ValueError("training and evaluation rows must not overlap")
        return self


def load_bundle(path: str | Path) -> Bundle:
    return Bundle.model_validate_json(Path(path).read_bytes())


def probabilities(x, w, b):
    logits = x @ w + b
    logits -= logits.max(axis=1, keepdims=True)
    exp = np.exp(logits)
    return exp / exp.sum(axis=1, keepdims=True)


def gradient(x, y, w, b):
    delta = probabilities(x, w, b)
    delta[np.arange(len(y)), y] -= 1
    return delta @ w.T


def train(x, y, classes, epochs=300):
    """Fixed full-batch softmax regression recipe for paired poisoning controls."""
    w, b = np.zeros((x.shape[1], classes)), np.zeros(classes)
    for _ in range(epochs):
        delta = probabilities(x, w, b)
        delta[np.arange(len(y)), y] -= 1
        w -= 0.5 * (x.T @ delta / len(y) + 0.001 * w)
        b -= 0.5 * delta.mean(axis=0)
    return w, b


def macro_f1(y, pred, classes):
    scores = []
    for label in range(classes):
        tp = np.sum((y == label) & (pred == label))
        denom = np.sum(y == label) + np.sum(pred == label)
        scores.append(2 * tp / denom if denom else 0.0)
    return float(np.mean(scores))


def run(job: dict) -> dict:
    started = time.monotonic()
    bundle = load_bundle(job["model_path"])
    x, y = np.array(bundle.X_test), np.array(bundle.y_test)
    w, b = np.array(bundle.weights), np.array(bundle.bias)
    clean = probabilities(x, w, b)
    pred = clean.argmax(axis=1)
    correct = pred == y
    eligible = int(correct.sum())
    if not eligible:
        raise ValueError("No correctly classified evaluation samples; ASR and robustness grade are undefined")
    seed = job.get("seed", 42)
    raw = {
        "scan_id": job["scan_id"], "engine": "numpy-linear-v1", "simulated": False,
        "clean_accuracy": float(correct.mean()), "sample_count": len(y),
        "eligible_count": eligible, "seed": seed, "params": job["params"],
        "model_sha256": hashlib.sha256(Path(job["model_path"]).read_bytes()).hexdigest(),
        "dataset_sha256": hashlib.sha256(json.dumps([bundle.X_test, bundle.y_test], separators=(",", ":")).encode()).hexdigest(),
        "dataset_description": bundle.description,
        "limitations": "Continuous [0,1] features; empirical results on supplied data, not a robustness certificate. Compare only identical datasets and attack budgets. Poisoning retrains a reference model, not the uploaded weights.",
    }
    for attack in job["attacks"]:
        p = job["params"][attack]
        rng = np.random.default_rng(seed)  # stable regardless of scan ID / attack ordering
        if attack in {"fgsm", "pgd"}:
            epsilon = p["epsilon"]
            adv = x.copy()
            if attack == "fgsm":
                adv = np.clip(x + epsilon * np.sign(gradient(x, y, w, b)), 0, 1)
            else:
                adv = np.clip(x + rng.uniform(-epsilon, epsilon, x.shape), 0, 1)
                for _ in range(p["iterations"]):
                    adv += p["step_size"] * np.sign(gradient(adv, y, w, b))
                    adv = np.clip(np.clip(adv, x - epsilon, x + epsilon), 0, 1)
            raw.setdefault("evasion", {})[attack] = outcomes(x, y, adv, w, b, clean, correct)
        elif attack == "random_search":
            # Decision-only search; budget counts candidate predictions PER eligible sample.
            adv = x.copy()
            active = np.flatnonzero(correct)
            queries = 0
            for _ in range(p["query_budget"]):
                if not len(active):
                    break
                candidate = np.clip(x[active] + rng.uniform(-p["epsilon"], p["epsilon"], (len(active), x.shape[1])), 0, 1)
                labels = probabilities(candidate, w, b).argmax(axis=1)
                queries += len(active)
                success = labels != y[active]
                adv[active[success]] = candidate[success]
                active = active[~success]
            block = outcomes(x, y, adv, w, b, clean, correct)
            block.update(queries_used=queries, query_budget=p["query_budget"], budget_unit="per eligible sample", maximum_queries=eligible * p["query_budget"])
            raw["black_box"] = {attack: block}
        elif attack == "poisoning":
            if bundle.X_train is None:
                raise ValueError("Label-flip poisoning requires separate X_train and y_train")
            tx, ty = np.array(bundle.X_train), np.array(bundle.y_train)
            cw, cb = train(tx, ty, len(b))
            baseline_pred = probabilities(x, cw, cb).argmax(axis=1)
            baseline = float(np.mean(baseline_pred == y))
            baseline_f1 = macro_f1(y, baseline_pred, len(b))
            order = rng.permutation(len(ty))
            raw["poisoning"] = {}
            for pct in p["contamination_pct"]:
                count = int(len(ty) * pct / 100)
                poisoned = ty.copy()
                poisoned[order[:count]] = (poisoned[order[:count]] + 1) % len(b)
                pw, pb = train(tx, poisoned, len(b))
                pp = probabilities(x, pw, pb).argmax(axis=1)
                accuracy = float(np.mean(pp == y))
                raw["poisoning"][f"{pct}pct"] = {
                    "accuracy_drop": max(0.0, baseline - accuracy),
                    "f1_drop": max(0.0, baseline_f1 - macro_f1(y, pp, len(b))),
                    "baseline_accuracy": baseline, "poisoned_accuracy": accuracy,
                    "poisoned_count": count, "training_count": len(ty),
                    "actual_contamination_pct": 100 * count / len(ty),
                    "recipe": "softmax regression, 300 epochs, lr=0.5, L2=0.001, zero initialization",
                }
        else:
            raise ValueError(f"Unsupported attack: {attack}")
    raw["duration_seconds"] = round(time.monotonic() - started, 4)
    return raw


def outcomes(x, y, adv, w, b, clean, correct):
    probs = probabilities(adv, w, b)
    predictions = probs.argmax(axis=1)
    success = correct & (predictions != y)
    ids = np.flatnonzero(success)[:10]
    return {
        "asr": float(success.sum() / correct.sum()),
        "success_count": int(success.sum()), "eligible_count": int(correct.sum()),
        "adversarial_accuracy": float(np.mean(predictions == y)),
        "avg_confidence_drop": float(np.mean((clean - probs)[np.arange(len(y)), y][correct])),
        "max_perturbation_linf": float(np.max(np.abs(adv - x))),
        "samples": [{"id": int(i), "orig_pred": int(clean[i].argmax()), "adv_pred": int(predictions[i]),
                     "true_label": int(y[i]), "conf_delta": float(clean[i, y[i]] - probs[i, y[i]]),
                     "perturbation_norm": float(np.max(np.abs(adv[i] - x[i]))),
                     "original": x[i].tolist(), "adversarial": adv[i].tolist()} for i in ids],
    }


def demo_bundle() -> dict:
    rng = np.random.default_rng(17)
    x = rng.uniform(0, 1, (600, 4))
    y = (x[:, 0] + 0.6 * x[:, 1] - 0.5 * x[:, 2] > 0.55).astype(int)
    w, b = train(x[:400], y[:400], 2)
    return Bundle(weights=w.tolist(), bias=b.tolist(), X_train=x[:400].tolist(), y_train=y[:400].tolist(),
                  X_test=x[400:].tolist(), y_test=y[400:].tolist(),
                  description="Synthetic continuous-feature binary classification benchmark; seed 17; 400 training / 200 held-out rows").model_dump()


if __name__ == "__main__":
    import sys
    try:
        print(json.dumps(run(json.load(sys.stdin)), allow_nan=False))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
