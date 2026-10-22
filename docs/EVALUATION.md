# Evaluation methodology and scope

The evaluator supports binary/multiclass linear-softmax classifiers with
continuous, already normalized [0,1] features. It does not execute arbitrary
sklearn pickles, ONNX, XGBoost, PyTorch, image models, or LLMs. Those require
separate adapters and hardened execution infrastructure. Old simulated results
are historical only; use new JSON uploads and scans for the demonstration.

## JSON input

```json
{
  "format": "linear-softmax-v1",
  "weights": [[-4, 4]], "bias": [2, -2],
  "X_test": [[0.1], [0.49], [0.51], [0.9]], "y_test": [0, 0, 1, 1],
  "X_train": [[0.05], [0.2], [0.8], [0.95]], "y_train": [0, 0, 1, 1],
  "description": "Known decision boundary at x=0.5"
}
```

Upload with model_type=linear_json. Weights are features by classes and the
prediction is argmax(softmax(XW+b)). Labels are indices 0..C-1. Limits: 128
features, 20 classes, 1000 evaluation rows, 2000 training rows, 10 MB. Training
data is optional except for poisoning. Exact overlapping training/test feature
rows are rejected. This cannot prove dataset quality or independence.

For fitted binary sklearn LogisticRegression, export weights as
column_stack([zeros(n_features), model.coef_[0]]) and bias as
[0, model.intercept_[0]]. Map model.classes_ to indices. For multinomial softmax
regression, export model.coef_.T and model.intercept_. Include preprocessed
held-out data and training data; preprocessing must be fit on training data only.
This is not a general sklearn converter. Categorical-feature constraints are
not modeled.

**Load example classifier** provides a real trained classifier with 400 training
and 200 held-out synthetic examples (seed 17). It makes no real-world domain
accuracy claims.

## Algorithms

- FGSM: analytic cross-entropy input gradient, epsilon times its sign, clipped to
  [0,1]. Epsilon is an L-infinity budget in normalized feature units.
- PGD: seeded random start, gradient ascent, projection into the epsilon ball and
  [0,1], at most 200 iterations. One restart, no certified robustness claim.
- Random search: decision-only uniform candidates in the same budget, early stop
  after success. The query budget is per initially correct sample and counts
  candidate predictions, excluding baseline evaluation. This is not HopSkipJump.
- Label flipping: deterministic nested subsets with cyclic replacement labels,
  followed by paired clean/poisoned reference softmax regression retraining:
  zero initialization, 300 epochs, learning rate 0.5, L2=0.001. Reports actual
  integer flip counts. Measures training-process sensitivity, not direct
  modification of the uploaded weights. No evaluation rows enter training.

## Metrics

ASR = successful misclassifications / initially correct evaluation samples.
If none were initially correct, the scan fails without a grade. Clean accuracy,
adversarial accuracy, successful/eligible counts, L-infinity norms and actual
original/adversarial example vectors are recorded. Zero observed impact does not
produce a vulnerability finding.

Category impact: mean ASR for evasion and black-box; mean nonnegative accuracy
loss over poisoning levels. Base weights 0.4/0.3/0.3 are renormalized across
**evaluated categories only**. Score = 100 * (1 - weighted impact).
A>=90, B>=75, C>=60, D>=40, else F. These are project-defined descriptive
thresholds, not an external certification. A high grade may coexist with poor
clean accuracy. Compare only identical datasets, attacks, budgets and seeds.
Single-seed experiments do not establish statistical significance; repeat with
multiple seeds for research claims (API seed parameter).

Results include model and evaluation-dataset SHA-256, effective parameters,
seed, engine version, runtime, sample counts and evidence. JSON export preserves
the full result. A planned extension is confidence intervals and multi-seed
aggregation; neither is currently implemented.

## Execution limits

Data-only JSON is validated without executing uploaded code. Evaluation runs in
a killable subprocess with a reduced environment. This is not an OS security
sandbox. At most two evaluators run per process; excess jobs fail with a retry
message. On restart unfinished jobs become failed. Use one worker and replica.
Production rejects the default signing key, limits POST requests and requires
authenticated report downloads. This is a small capstone deployment, not a fully
hardened multi-tenant service. Add storage quotas/backups, external abuse
monitoring and durable workers before larger-scale use.

## References and mappings

- FGSM: https://arxiv.org/abs/1412.6572
- PGD: https://arxiv.org/abs/1706.06083
- Evasion: https://atlas.mitre.org/techniques/AML.T0015 (Impact AML.TA0011)
- Poisoning: https://atlas.mitre.org/techniques/AML.T0020 (Resource Development AML.TA0003)
- Mappings checked 2026-10-21 against MITRE's published legacy catalogue v5.6.0:
  https://github.com/mitre-atlas/atlas-data/blob/main/dist/ATLAS.yaml

The mapper is a pinned project subset, not an automatically updated catalogue.
OWASP/NIST references are contextual pointers, not compliance determinations.
