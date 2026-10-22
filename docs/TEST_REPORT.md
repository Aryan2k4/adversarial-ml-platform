# Capstone verification - 2026-10-21

## Result

53 automated tests pass in the final Linux production image (Python 3.12), and
also pass on the local Python 3.14 installation. The local interpreter has older
installed packages; the production image installs the pinned requirements.
Frontend production build passes. npm audit reports zero advisories; pip-audit
on the updated container reports zero vulnerable packages (70 packages audited,
including audit tooling). Audit results are point-in-time, not a security guarantee.

## Defects corrected

- Fabricated random scan outcomes replaced with real model/dataset evaluation.
- Fake executable model uploads rejected; supported data-only JSON format validated.
- Partial attack selections no longer gain credit for untested categories.
- ASR measured over initially correct samples; undefined ASR cannot earn a grade.
- Killable subprocess deadline replaces the ineffective thread-pool timeout.
- Effective parameters, sample evidence, hashes, counts and seed are recorded.
- Unsupported HopSkipJump removed from advertised capabilities; decision-only
  random search is accurately labeled.
- ATLAS technique/tactic mappings corrected; zero impact creates no finding.
- Parameter bounds, dimensions, non-finite values and train/test overlap validated.
- Report authentication moved from query strings to Authorization headers.
- Cross-account authorization and frontend cache isolation verified/fixed.
- Password UTF-8 byte length bounded for bcrypt; malformed JWT subjects rejected.
- Production secret guard, request rate limits and evaluator concurrency limits added.
- Restarted jobs become failed instead of remaining stuck forever.
- Single-origin serving and persistent storage added; static-file path corrected.
- Browser number-input step constraints corrected for default PGD settings.
- Dependencies upgraded; Tailwind/Vite compatibility and font paths corrected.
- Report long fields wrap; model hashes are no longer truncated.

## Numerical checks

Analytic input gradients agree with finite differences. A known boundary model
returns exactly 50% FGSM ASR at epsilon 0.05. Zero-epsilon experiments do not
perturb inputs. PGD is repeatable and obeys its L-infinity projection. Query
budgets are counted. Zero-contamination poisoning matches the clean retraining
control. No initially correct examples produces no grade.

## Production acceptance

Browser: register -> load example -> configure all four attacks -> polling ->
completed results. Default PGD form validation was exercised and fixed.
API: authenticated upload -> all four attacks -> score/findings/history -> PDF
and HTML export. JSON evidence saved. Container restart preserved login, model,
completed scan, score, and evidence. Refresh/deep-link routing is tested.
All four generated PDF pages were rendered and visually inspected for clipping
and readability. Browser results screenshot and scan JSON are in artifacts/.

Synthetic example (200 held-out rows, seed 42, epsilon 0.05):
- Clean accuracy: 99.5%; 199 initially correct.
- FGSM and PGD: 38/199 successes (19.095% ASR); 80.5% adversarial accuracy.
- Random search: 30/199 successes (15.075% ASR), 100 queries/sample maximum.
- Label-flip accuracy losses: 0%, 0.5%, 3% at 1%, 5%, 10% contamination.
- Combined empirical score: 87.5 (B). This is not a certified robustness result.

## Remaining scope and hosting limits

Supports linear-softmax classifiers with normalized continuous features only.
No arbitrary pickle/PyTorch/ONNX/XGBoost, LLM adapters, HopSkipJump, certified
bounds, statistical significance claims, or multi-replica durable queue.
Poisoning evaluates paired reference retraining. It does not alter uploaded weights.
Read EVALUATION.md before making capstone claims. Run representative real-world
held-out datasets for the final academic evaluation; the included demo is synthetic.

On 2026-10-22 the source was published to Aryan2k4/adversarial-ml-platform and
GitHub CI passed. At the user's request, render.yaml now selects the free tier.
The local named-volume restart test above does not apply to the free hosted demo:
Render resets local SQLite and uploaded files on sleep, restart or redeploy.
No persistent cloud disk or paid service is configured. See DEPLOYMENT.md.

