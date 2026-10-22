> Historical milestone document. The current evaluator and deployment are documented in the root README and docs/EVALUATION.md; mock and sandbox claims below describe the original scaffold.

# HANDOFF — M1's work, Milestones 1 through 6

Everything the software owner (M1) is responsible for across all six milestones is built and
running. The platform works end to end today: register, upload a model, configure a scan, watch it
run, read the scorecard, download a compliance report. The attacks behind it are mocked, because
M2, M3 and M4 haven't started — and that's the only thing left.

## What's real

**Backend** — FastAPI + SQLAlchemy 2.0 + Alembic on Postgres 15.
Auth (bcrypt hashing, JWT access + refresh, expiry handling), the full schema from ARCHITECTURE.md
section 7, multipart model upload with suffix/size/sha256 validation, scan creation as a
BackgroundTask, status polling, score and findings endpoints, score history, PDF and HTML report
export, structured JSON logging, per-row ownership checks, a timeout backstop, and a global
exception handler that never leaks a traceback. 14 tests pass; `alembic check` reports no drift.

**Frontend** — React 18 + Vite + Tailwind + React Query + Zustand + Recharts + Framer Motion.
Five screens, no mock data, real API only. Polling stops on its own when a scan settles. Error,
empty and loading states everywhere, including "the API is unreachable" and "your session expired".

**Deployment** — `backend/Dockerfile` (migrations at boot), `frontend/vercel.json`,
`docs/DEPLOYMENT.md` for Supabase + Railway/Render + Vercel.

## What's mocked

Three functions, each in its own module, each called from exactly one place:

| Seam | File | Owner |
|---|---|---|
| `run_scan(job_config) -> raw_results` | `backend/app/services/sandbox_client.py` | M2 |
| `score_results(raw_results) -> score` | same file | M2 |
| `get_findings(raw_results, score) -> findings` | `backend/app/services/atlas_client.py` | M3 |

M4's attack code is never called by the backend at all — it runs inside M2's container and
communicates only by writing `raw_results.json`.

The mock scoring formula and severity thresholds are ARCHITECTURE.md sections 5 and 6 verbatim, so
a faithful real implementation produces the same numbers and the contract tests keep passing.
Report *copy* is M1 placeholder text until M3 hands over their template — only the strings in
`app/services/report.py` change when it does.

## File tree

```
/
├── README.md · docker-compose.yml · .gitignore
├── backend/
│   ├── README.md · requirements.txt · .env.example · alembic.ini · Dockerfile · .dockerignore
│   ├── alembic/{env.py, script.py.mako, versions/0001_initial_schema.py}
│   ├── scripts/seed_demo.py
│   ├── app/
│   │   ├── main.py
│   │   ├── core/{config,security,logging}.py
│   │   ├── db/{base,session}.py
│   │   ├── schemas/{common,auth,model,scan}.py
│   │   ├── api/deps.py + api/routes/{health,auth,models,scans,reports}.py
│   │   ├── services/{contracts,sandbox_client,atlas_client,pipeline,report}.py
│   │   └── fixtures/*.example.json
│   └── tests/{conftest,test_auth,test_scans,test_contracts,test_reports}.py
├── frontend/
│   ├── README.md · package.json · vite.config.js · tailwind.config.js · vercel.json · index.html
│   └── src/
│       ├── main.jsx · App.jsx · styles/index.css
│       ├── lib/api.js · store/auth.js
│       ├── components/{Layout.jsx, primitives.jsx}
│       └── pages/{Login,Models,NewScan,ScanDetail,ModelHistory}.jsx
├── sandbox/README.md · attack_engine/README.md · atlas/README.md   (placeholders, M2/M4/M3)
└── docs/{ARCHITECTURE,PROJECT_LOG,HANDOFF,INTEGRATION,DEPLOYMENT}.md
```

## Run the whole thing

```bash
docker compose up -d db
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && cp .env.example .env
alembic upgrade head
python -m scripts.seed_demo          # optional: demo@redteam.local / demo-password-123
uvicorn app.main:app --reload        # :8000, Swagger at /docs

cd ../frontend && npm install && npm run dev     # :5173
```

## Deviations

Twelve, all listed in PROJECT_LOG.md's DECISIONS / DEVIATIONS with a reason each. The ones a
teammate should actually know about: schema section 7 gained six columns (ARCHITECTURE.md edited to
match), section 8 was rewritten to the real route list, the report endpoint takes its JWT as a query
param, and a backend-side scan timeout was added on top of M2's container kill.

## What's left, and who owns it

Nothing further for M1 until other people's code exists. When it does:

1. M2 replaces two functions in `sandbox_client.py`; M3 replaces one in `atlas_client.py`.
   `INTEGRATION.md` has the exact diff each of them needs.
2. M3's report template replaces the placeholder copy in `report.py`.
3. Deploy per `DEPLOYMENT.md`, then run the four-way integration checkpoint from
   TEAM_ROLES_AND_MILESTONES.docx and close the milestone entries in `PROJECT_LOG.md`.
4. Record the demo; write the paper sections each owner is down for.

If a scan hangs after real services land, the first thing to check is
`SCAN_TIMEOUT_SECONDS` versus how long M2's container actually takes to retrain on a poisoning run.
