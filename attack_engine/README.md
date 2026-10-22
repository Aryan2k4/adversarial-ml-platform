> Historical milestone document. The current evaluator and deployment are documented in the root README and docs/EVALUATION.md; mock and sandbox claims below describe the original scaffold.

# /attack_engine — M4 (AI/ML)

Your code goes here. Runs *inside* M2's container, never called by the backend directly.

Contract: read `job_config.json` (ARCHITECTURE.md contract #3) from the mounted volume, write
`raw_results.json` (contract #4) back to the output volume. `backend/app/fixtures/` has frozen
examples of both — build against those and your output will drop straight in.

The backend stores contract #4 verbatim in `raw_results.json_blob`, so the shape is yours to own —
just don't change it without editing ARCHITECTURE.md section 4.
