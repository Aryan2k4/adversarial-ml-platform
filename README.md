# Adversarial ML Red-Teaming Platform

A capstone application for real, reproducible adversarial evaluation: FastAPI,
React, authenticated uploads, FGSM, PGD, decision-only random search, label-flip
experiments, empirical robustness grades, ATLAS findings, and PDF/HTML/JSON exports.

**Current scope:** binary and multiclass linear-softmax classifiers exported as
JSON coefficients plus labeled datasets. Arbitrary pickle, PyTorch, ONNX and
XGBoost artifacts are not executed. Historical scans from the original mock
pipeline are not evidence of real evaluation; upload a new JSON bundle.

## Local setup

Use Python 3.12 and Node 22 (matching the production container).

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Fresh checkout only: preserve any existing .env.
Copy-Item .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

In another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173, register, click **Load example classifier**, then
**Run a scan**. The example uses a real trained model and synthetic held-out data.
No shared demo credentials are needed.

## Verification

```powershell
cd backend
python -m pytest -q
cd ../frontend
npm run build
npm audit
cd ..
docker build -t adversarial-ml-capstone:tested .
docker run --rm adversarial-ml-capstone:tested python -m pytest -q
```

The root Dockerfile serves both frontend and API. `render.yaml` defines one paid
service with persistent storage and a generated JWT key. See
[deployment](docs/DEPLOYMENT.md) and [evaluation methodology](docs/EVALUATION.md).
Hosting account access is required before a public URL can be issued.

Older milestone documents are retained as historical handoff notes. This README
and EVALUATION.md describe the current implementation.

