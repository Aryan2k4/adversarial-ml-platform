# Permanent deployment

Use one Render Docker web service with a persistent disk. The UI and API share
one HTTPS origin; separate frontend hosting and CORS configuration are unnecessary.

1. Install/connect Render and sign in or create your hosting account.
2. Put this source in a private GitHub repository and authorize Render to read it.
   Exclude .env, databases, uploaded data, node_modules, and test artifacts.
3. Create a Render Blueprint using the root `render.yaml`.
4. Review the Starter service and 1 GB disk charges before confirming creation.
   Render requires a paid service for persistent disks.
5. Wait for deployment success and copy the actual assigned HTTPS URL. Do not
   infer the URL from the service name.

The root Dockerfile builds React and mounts the API at /api. /api/health must
return HTTP 200 and database=up. SQLite and uploads live under /app/storage on the
persistent disk. Migrations run at boot. Keep the generated JWT secret stable.

## Acceptance checks

Register; load the example; run all four experiments; download PDF/HTML/JSON;
refresh a scan deep link; restart the service and verify accounts, uploaded
bundles, and completed scans remain. Interrupted scans must show a failed status
with a retry message. Verify another account cannot access the first account's
models, scans, or reports.

## Operations

Use one replica and one Uvicorn worker. At most two evaluations run concurrently.
Move to a durable job queue and shared storage before scaling. Keep database-
consistent backups and disk snapshots. Add storage quotas and external abuse
monitoring for larger public use. The public URL remains available while the
hosting account and service are maintained and billing remains current.

Sources: https://render.com/docs/blueprint-spec and https://render.com/docs/disks
