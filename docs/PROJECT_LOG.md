# PROJECT LOG — read this first

> **Instructions for whoever (human or AI) picks this project up next:**
> 1. Read `ARCHITECTURE.md` for the system design and contracts.
> 2. Read the "CURRENT STATUS" block below — it tells you exactly which milestone is active and
>    what's done vs pending.
> 3. When a milestone is completed by all 4 members, append a new dated entry under
>    "MILESTONE HISTORY" (copy the template) BEFORE starting the next milestone's work.
> 4. If any contract in ARCHITECTURE.md changes, edit that file directly and note the change
>    in this log's "DECISIONS / DEVIATIONS" section — don't let the two files drift apart.
> 5. Keep entries short and factual (what shipped, what broke, what's still fake/stubbed).

---

## CURRENT STATUS
- **Active milestone:** M1–M6 for the M1 (Software) owner are **all complete**. The project is
  blocked on M2/M3/M4, not on the platform.
- **M1 (Software): DONE through Milestone 6** — backend, DB, auth, full API surface, PDF/HTML
  report export, React frontend wired to the real API, deployment config. See `HANDOFF.md`.
- **M2 / M3 / M4: not yet started.** Their real services drop into three mocked seams with no
  backend refactor — see `INTEGRATION.md`. No milestone can be *closed* (integration checkpoint,
  history entry) until all four owners are done.
- Last updated: 2026-09-20

---

## DECISIONS / DEVIATIONS
_(Log anything that changes from ARCHITECTURE.md's default plan — e.g. "switched Celery for
FastAPI BackgroundTasks", "using SQLite locally instead of Postgres until M2", etc. One line each.)_

- Schema section 7 gained columns during implementation (`models.checksum_sha256`,
  `models.size_bytes`, `scans.error`, `scores.weights`, `findings.evidence`,
  `raw_results.created_at`) — ARCHITECTURE.md section 7 edited to match.
- Milestone-2 routes (`POST /models` real upload, `POST /scans` + BackgroundTask,
  `GET /scans/{id}`) built during M1 so the OpenAPI contract published at M1 is the final shape
  teammates code against, not one that changes under them in five days.
- JWT enforced on all model/scan routes now, though M1's task list allowed leaving routes open —
  cheaper to do once than to retrofit.
- `docker-compose.yml` for local Postgres pulled forward from M5; migrations need a DB to apply to.
- bcrypt used directly instead of passlib (passlib 1.7.4 has known breakage with bcrypt 4.x).
- M2/M3/M4 outputs are mocked behind `sandbox_client.py` / `atlas_client.py`. The mock scoring
  formula and severity thresholds are ARCHITECTURE.md sections 5 and 6 verbatim, so the real
  engines should reproduce the same numbers for the same input.
- SQLAlchemy column types use `JSON().with_variant(JSONB, "postgresql")` and `sa.Uuid` so tests
  run on SQLite while production stays on Postgres 15 — one schema definition, no fork.
- `ARCHITECTURE.md` and `PROJECT_LOG.md` now live in `/docs` per section 2's repo layout.
- ARCHITECTURE.md section 8 rewritten to list the routes that actually exist (health, refresh, me,
  models list, score, findings, report with its query-param token, ownership rules).
- Report auth uses `?token=<jwt>` on `GET /scans/{id}/report` — a browser downloading via a link
  click can't attach an Authorization header. Same JWT, same expiry, different carrier.
- Report content is M1's placeholder copy until M3 hands over their template; only the copy in
  `app/services/report.py` changes when it lands, not the export plumbing.
- Backend-side scan timeout backstop (`SCAN_TIMEOUT_SECONDS`, default 600) added on top of M2's
  container-level kill, so a hung sandbox can't leave a scan stuck on "running" forever.
- Frontend uses a Vite dev proxy (`/api` → localhost:8000) so dev never hits CORS; production uses
  `VITE_API_URL` and the backend's `CORS_ORIGINS` list.
- General Sans loads from Fontshare rather than being committed to the repo (licence/binary size);
  `@font-face` block and instructions for fully self-hosting are in `frontend/src/styles/index.css`.
  Inter Tight *is* self-hosted via `@fontsource`.
- Mitigation checklist ticks are stored in the browser's localStorage, not the DB — they're a user's
  working notes, and a `finding_status` table isn't worth the migration for a 1-month build.
- `backend/scripts/seed_demo.py` added so a demo doesn't start on an empty dashboard.

---

## MILESTONE HISTORY
_(Copy this template for each completed milestone.)_

### Template
```
## M<N> — <name> — completed <date>
Owner status:
- M1 (Software): <what shipped> | <what's stubbed/fake> | <blockers>
- M2 (Cyber-1):  <...>
- M3 (Cyber-2):  <...>
- M4 (AI/ML):    <...>

Integration test result: <pass/fail + what was tested end-to-end>
Files/paths touched: <list>
Known issues carried into next milestone: <list>
```

_(No milestone is complete until all four owners are done — M1 alone doesn't close a milestone.
The entries below record M1's slice only; fill in M2/M3/M4 and each integration result as they
land.)_

## M1 — Skeleton & Contracts — M1's slice completed 2026-09-20
Owner status:
- M1 (Software): repo scaffold, FastAPI app + health check, full Postgres schema via
  SQLAlchemy 2.0 + Alembic (`0001`), JWT auth (register/login/refresh/me) with bcrypt, model
  upload with suffix/size/sha256 validation, `POST /scans` + BackgroundTask pipeline,
  `GET /scans/{id}`, score history route, OpenAPI/Swagger published, 10 passing tests.
  | Stubbed: sandbox, attack engine, scoring engine and ATLAS mapper are contract-shaped mocks
  behind two client modules. | Blockers: none.
- M2 (Cyber-1):  not started
- M3 (Cyber-2):  not started
- M4 (AI/ML):    not started

Integration test result: internal only — `pytest` proves job_config → raw_results → score →
findings → DB → API round-trips in the documented shapes. The real four-way checkpoint (M4's
model through M2's container, M3's lookup) still has to be run by hand.
Files/paths touched: `/backend/**`, `/docs/**`, `docker-compose.yml`, `README.md`,
placeholder READMEs in `/sandbox`, `/attack_engine`, `/atlas`, `/frontend`.
Known issues carried into next milestone: uploaded artefacts go to local disk (fine until
deployment); no rate limiting on auth routes; refresh tokens aren't revocable (no denylist);
BackgroundTasks die with the process — acceptable for a 1-month build, noted for the paper's
limitations section.

## M2 — Real Sandbox + PGD + Auth — M1's slice completed 2026-09-20
Owner status:
- M1 (Software): real multipart upload (suffix + 200 MB streaming limit + sha256), `POST /scans`
  with a FastAPI BackgroundTask, `GET /scans/{id}` status polling, JWT enforced on every model and
  scan route with per-row ownership checks (404 on someone else's id).
  | Stubbed: the sandbox itself. | Blockers: none.
- M2 / M3 / M4: not started.

Integration test result: internal — `test_scans.py` covers upload validation, a full scan, and the
ownership/401 paths.
Files/paths touched: `backend/app/api/routes/{models,scans}.py`, `backend/app/services/pipeline.py`.
Known issues carried into next milestone: artefacts on local disk only.

## M3 — Black-box Attacks + Scoring Engine v1 — M1's slice completed 2026-09-20
Owner status:
- M1 (Software): `GET /scans/{id}/score` (409 while unfinished) and `GET /scans/{id}/findings`
  (ranked by severity), `GET /models/{id}/scans` for score history, and the failure path —
  background-task exceptions are caught, logged, and persisted to `scans.status=failed` +
  `scans.error`, with a `SCAN_TIMEOUT_SECONDS` backstop for a sandbox that never returns.
  | Stubbed: scoring engine is still M1's mock of contract #5. | Blockers: none.
- M2 / M3 / M4: not started.

Integration test result: internal — `test_failed_scan_surfaces_its_error` forces a sandbox
exception and asserts the API reports it instead of hanging.
Files/paths touched: `backend/app/api/routes/scans.py`, `backend/app/services/pipeline.py`,
`backend/app/core/config.py`.
Known issues carried into next milestone: a scan interrupted by a process restart stays `running`.

## M4 — Poisoning Simulation + Frontend Skeleton — M1's slice completed 2026-09-20
Owner status:
- M1 (Software): React 18 + Vite + Tailwind + React Query + Zustand frontend, wired to the real API
  with no mock data anywhere — login/register, model upload, scan configuration with per-attack
  parameters, live status polling that stops when the status settles, scorecard with a Recharts
  per-attack ASR bar chart. | Stubbed: nothing on the frontend; the data behind it is still mocked
  server-side. | Blockers: none.
- M2 / M3 / M4: not started.

Integration test result: internal — frontend builds clean and drives the real backend end to end
(register → upload → scan → scorecard) against the mocked pipeline.
Files/paths touched: `frontend/**`.
Known issues carried into next milestone: no frontend unit tests (deliberate — the API contract
tests are where the value is for a build this size).

## M5 — Dashboard Polish + Reports + Deployment — M1's slice completed 2026-09-20
Owner status:
- M1 (Software): ATLAS technique table and remediation checklist views, `GET /scans/{id}/report`
  exporting a paginated PDF (ReportLab) and a styled HTML page, score-history trend chart,
  `backend/Dockerfile` with migrations at boot, `frontend/vercel.json`, and `docs/DEPLOYMENT.md`
  covering Supabase + Railway/Render + Vercel.
  | Stubbed: report *content* is M1 placeholder copy until M3's template arrives; layout and export
  are final. | Blockers: needs M3's report content and a real deploy to be signed off.
- M2 / M3 / M4: not started.

Integration test result: internal — `test_reports.py` asserts a real PDF byte stream, the HTML
variant, ATLAS IDs present in the output, and a 401 on a bad token.
Files/paths touched: `backend/app/services/report.py`, `backend/app/api/routes/reports.py`,
`backend/Dockerfile`, `frontend/src/pages/{ScanDetail,ModelHistory}.jsx`, `docs/DEPLOYMENT.md`.
Known issues carried into next milestone: ephemeral artefact storage on a single instance.

## M6 — Testing, Hardening, Paper & Demo — M1's slice completed 2026-09-20
Owner status:
- M1 (Software): error, empty and loading states on every screen (unreachable API, expired session,
  failed scan with its reason, no models yet, no trend data yet), retry buttons on every failed
  query, 401 auto-signs-out instead of looping, `prefers-reduced-motion` respected, keyboard focus
  visible, responsive to mobile, demo seed script, 14 backend tests passing.
  | Stubbed: nothing further. | Blockers: the paper and demo video need M2/M3/M4's sections.
- M2 / M3 / M4: not started.

Integration test result: internal — full `pytest` suite green; manual end-to-end (register →
upload → four-attack scan → scorecard → PDF) run against the mocked pipeline.
Files/paths touched: `frontend/src/**`, `backend/tests/**`, `backend/scripts/seed_demo.py`.
Known issues carried into next milestone: everything left is M2/M3/M4 integration, a real deploy,
and the paper.

---

## RESEARCH PAPER TRACKER
_(Fill in as milestones complete — this becomes the paper's backbone.)_

| Paper section | Status | Source milestone | Owner |
|---|---|---|---|
| Abstract | pending | M6 | M3 |
| Related Work / Literature Comparison | done (see Literature_Comparison_Adversarial_ML_Platform_final.xlsx) | pre-project | M3 |
| Research Gap statement | done (see xlsx "Key Gaps Summary" sheet) | pre-project | M3 |
| Methodology (sandbox + pipeline) | pending | M2, M5 | M2 |
| Attack Engine methodology | pending | M1–M4 | M4 |
| Scoring formula justification | pending | M3 | M2 |
| Compliance mapping (OWASP/NIST/ATLAS) | pending | M3 | M3 |
| Results / benchmarks | pending | M5 | M4 |
| Conclusion & Future Scope | pending | M6 | all |

**M1's contribution to the paper** (raw material, not yet written up): the JSON-contract-first
architecture that let four people build in parallel is itself a methodology point; the mocked-seam
approach (contract fixtures standing in for unbuilt modules) belongs in Methodology; the
limitations list in `DEPLOYMENT.md` feeds Future Scope.
