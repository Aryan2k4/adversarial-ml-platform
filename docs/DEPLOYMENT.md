# Free deployment

The root render.yaml deploys a free Docker web service with no paid disk.
The frontend and API share one HTTPS origin. Connect the private GitHub repository
in Render, create a Blueprint, and select main. No paid resources are configured.

## Data and availability limits

This is a capstone demonstration, not durable production hosting. Render's free
service sleeps after 15 minutes without inbound traffic and takes about a minute
to wake. Its local SQLite database and uploaded bundles are lost on spin-down,
restart or redeploy. Download PDF/HTML/JSON results before leaving; register again
if your account has been reset. VITE_FREE_DEMO=true displays this warning in the UI.
The assigned public URL remains tied to the service, subject to Render account,
usage and availability limits; it is not a guarantee of permanent availability.

Free Render Postgres expires after 30 days and is deliberately not provisioned.
Durable free hosting requires an external database plus durable model storage;
those are not part of this deployment. Do not treat local disk as persistent.

## Runtime and checks

One replica, one Uvicorn worker, at most two concurrent evaluations. Migrations
run at boot. /api/health must return 200 with database=up. Test registration,
example upload, all four attacks, report downloads and scan deep links. The
Docker image runs as a non-root user and generates no shared demo credentials.
Keep the generated JWT secret stable. Paid persistent hosting can later attach
/app/storage as a persistent disk on a paid service and disable VITE_FREE_DEMO.

Source: https://render.com/docs/free
