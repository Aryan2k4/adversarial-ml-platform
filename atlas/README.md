> Historical milestone document. The current evaluator and deployment are documented in the root README and docs/EVALUATION.md; mock and sandbox claims below describe the original scaffold.

# /atlas — M3 (Cybersecurity #2)

Your code goes here: `atlas_catalogue.json`, `mitigation_engine.py`, `compliance_map.json`.

What the backend expects, eventually:

```python
# atlas/mitigation_engine.py
def get_findings(raw_results: dict, score: dict) -> dict:
    """contracts #4 + #5 in, contract #6 (findings.json) out."""
```

That's exactly the signature `backend/app/services/atlas_client.py` calls today with a four-entry
mock catalogue. Replace it with the real lookup and the API starts serving your ATLAS IDs,
mitigations, OWASP and NIST refs with no backend changes. See `/docs/INTEGRATION.md`.

Severity thresholds currently mocked as ASR ≥0.6 high / ≥0.3 medium / else low — if you change them
in Milestone 2, update ARCHITECTURE.md contract #6 too.
