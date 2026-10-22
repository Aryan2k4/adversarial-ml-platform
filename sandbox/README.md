> Historical milestone document. The current evaluator and deployment are documented in the root README and docs/EVALUATION.md; mock and sandbox claims below describe the original scaffold.

# /sandbox — M2 (Cybersecurity #1)

Your code goes here. Nothing in this folder exists yet; M1 has only reserved the space.

What the backend expects from you, eventually:

```python
# sandbox/sandbox_manager.py
def run_scan(job_config: dict) -> dict:
    """job_config = ARCHITECTURE.md contract #3. Returns contract #4 (raw_results.json)."""

# sandbox/scoring_engine.py
def score_results(raw_results: dict) -> dict:
    """contract #4 in, contract #5 (score.json) out."""
```

Those two signatures are already what `backend/app/services/sandbox_client.py` calls, so the merge
is a delete-the-mock-and-import job. See `/docs/INTEGRATION.md`.

Nothing in `/backend` reads your container config, paths, or env vars — keep it that way.
