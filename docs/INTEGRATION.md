> Historical milestone document. The current evaluator and deployment are documented in the root README and docs/EVALUATION.md; mock and sandbox claims below describe the original scaffold.

# INTEGRATION — how to plug your real service in

The backend currently calls three mocks. Each one is a plain function with the signature your real
code will have, in its own module, called from exactly one place (`app/services/pipeline.py`).
Replacing a mock is a delete-and-import, not a refactor. Nothing else in `/backend` changes.

If your real output doesn't match ARCHITECTURE.md, `pytest backend/tests/test_contracts.py` fails
loudly — run it after you wire in.

---

## M2 — sandbox + scoring

**File to change:** `backend/app/services/sandbox_client.py`
**Functions:** `run_scan(job_config) -> raw_results` and `score_results(raw_results) -> score`

Delete both mock bodies and delegate:

```python
from sandbox.sandbox_manager import run_scan as _real_run_scan
from sandbox.scoring_engine import score_results as _real_score

def run_scan(job_config: dict) -> dict:
    return _real_run_scan(job_config)
```

You receive contract #3 already built and defaulted (`app/services/contracts.build_job_config` fills
in documented per-attack params). You return contract #4. `score_results` takes #4 and returns #5.
The mock's scoring maths is ARCHITECTURE.md section 5 verbatim, so if your engine is v1-faithful
the existing tests keep passing. `_mock_raw_results` and `grade_for` can go with it; keep
`contracts.assert_*` calls if you want the shape guard.

Note the backend never sees your container, paths, or resource flags — it hands you a dict and gets
a dict back. Keep it that way and deployment stays your call alone.

---

## M3 — ATLAS + mitigations

**File to change:** `backend/app/services/atlas_client.py`
**Function:** `get_findings(raw_results, score) -> findings`

```python
from atlas.mitigation_engine import get_findings as _real_get_findings

def get_findings(raw_results: dict, score: dict) -> dict:
    return _real_get_findings(raw_results, score)
```

Then delete `_MOCK_CATALOGUE`, `_finding`, and `severity_for` — your catalogue and your thresholds
replace them. Each entry in `findings[]` must carry `attack`, `atlas_tactic`, `atlas_technique`,
`severity`, `evidence`, `mitigation`, `owasp_ml_top10`, `nist_ai_rmf`; the API maps `owasp_ml_top10`
→ `findings.owasp_ref` and `nist_ai_rmf` → `findings.nist_ref` in the DB and maps them back on read,
so use the contract names, not the column names.

If you change severity thresholds, edit ARCHITECTURE.md contract #6 and log it in PROJECT_LOG.md.

---

## M4 — attack engine

**No backend file to change.** Your code runs inside M2's container and never talks to the API.

Read `job_config.json` (contract #3) from the mounted volume; write `raw_results.json` (contract #4)
to the output volume. Frozen examples of both are in `backend/app/fixtures/` — build against those.

The backend stores your JSON verbatim in `raw_results.json_blob` and returns it unmodified on
`GET /scans/{id}`, so nothing reshapes your output behind your back. Adding a new attack block means
editing ARCHITECTURE.md section 4 first, then telling M2 (scoring) and M3 (findings).

---

---

## M3 — report content (Milestone 5)

**File to change:** `backend/app/services/report.py`

The PDF and HTML layouts, pagination and download plumbing are done. What's placeholder is the
prose: `REPORT_INTRO` and the section headings. Hand over your template copy and it drops straight
in — don't rewrite the ReportLab code, and don't add a second export path.

If your template needs a field the report doesn't have (an executive summary per severity band, a
compliance coverage table), say so and M1 adds it to `_report_data()`.

---

## Checklist when you merge

1. `cd backend && pip install -r requirements.txt && pytest -q` — contract tests must pass.
2. `alembic upgrade head` — if you needed a schema change, ask M1; `/backend/app/db` stays M1-owned.
3. Trigger a real scan: `POST /auth/register` → `POST /models` → `POST /scans` → poll
   `GET /scans/{id}` until `status=done`.
4. Update `PROJECT_LOG.md` (DECISIONS / DEVIATIONS + your line in the milestone entry).
