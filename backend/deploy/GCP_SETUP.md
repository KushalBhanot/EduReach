# Going live on GCP (about 60 to 90 minutes, once)

Everything below is run by you. Each step creates or changes something in your Google Cloud account, so read it before you paste it. Replace `PROJECT_ID` everywhere (for example `edureach-fde`). The region is `us-central1` throughout.

Cost guardrails come first, in step 2. The expected bill for the build window is about $15 to $20, inside the $300 trial credit (see `docs/v2-plan.md` §6).

## 1. Install the CLI and log in

```bash
brew install --cask gcloud-cli
```

```bash
gcloud auth login
```

```bash
gcloud auth application-default login
```

## 2. Project, billing guardrails, APIs

Create the project in the console (console.cloud.google.com, New Project), start the free trial and link billing. Then:

```bash
gcloud config set project PROJECT_ID
```

Budget alerts at $25 and $50 (Billing > Budgets & alerts in the console is easiest).

```bash
gcloud services enable run.googleapis.com aiplatform.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com cloudtrace.googleapis.com
```

## 3. Check which models the project can call

```bash
cd backend && uv run python -m scripts.hello_vertex --project PROJECT_ID
```

If an ID in `app/models.py` is not listed, change it there before deploying.

## 4. Cloud SQL for PostgreSQL with pgvector

Smallest shared-core instance. Stop it when you won't use it for a day (`gcloud sql instances patch edureach-db --activation-policy NEVER`); only storage is billed while stopped.

```bash
gcloud sql instances create edureach-db --database-version POSTGRES_17 --tier db-f1-micro --region us-central1 --storage-size 10 --edition ENTERPRISE
```

```bash
gcloud sql databases create edureach --instance edureach-db
```

```bash
gcloud sql users create edureach_api --instance edureach-db --password "$(openssl rand -base64 24)"
```

Write that password down somewhere safe (a password manager). It goes into Secret Manager in step 6 and nowhere else. `CREATE EXTENSION vector` runs automatically the first time `ingest.load` applies the schema.

## 5. Load the textbooks from your laptop

Start the Cloud SQL Auth Proxy in its own terminal tab (install it with `gcloud components install cloud-sql-proxy` if needed):

```bash
cloud-sql-proxy PROJECT_ID:us-central1:edureach-db --port 5434
```

Then, in another tab, load the books. The OpenStax sources are already in `backend/data/raw/`. Embeddings come from `data/embed_cache/` (same model and dimensions), so this costs almost nothing:

```bash
cd backend && GOOGLE_CLOUD_PROJECT=PROJECT_ID EMBED_BATCH=100 DATABASE_URL="postgresql://edureach_api:PASSWORD@localhost:5434/edureach" uv run python -m ingest.load
```

Run it twice. The second run should report `inserted: 0` for every book. That is the idempotency check.

## 6. Service account and secret

```bash
gcloud iam service-accounts create edureach-api --display-name "EduReach API"
```

```bash
for role in roles/aiplatform.user roles/cloudsql.client roles/secretmanager.secretAccessor roles/cloudtrace.agent; do gcloud projects add-iam-policy-binding PROJECT_ID --member serviceAccount:edureach-api@PROJECT_ID.iam.gserviceaccount.com --role $role; done
```

The connection string goes into Secret Manager, never into the image or the app:

```bash
printf 'postgresql://edureach_api:PASSWORD@/edureach?host=/cloudsql/PROJECT_ID:us-central1:edureach-db' | gcloud secrets create edureach-database-url --data-file=-
```

## 7. Deploy

```bash
cd backend && gcloud run deploy edureach-api --source . --region us-central1 --service-account edureach-api@PROJECT_ID.iam.gserviceaccount.com --add-cloudsql-instances PROJECT_ID:us-central1:edureach-db --set-secrets DATABASE_URL=edureach-database-url:latest --set-env-vars GOOGLE_CLOUD_PROJECT=PROJECT_ID --allow-unauthenticated --min-instances 0 --max-instances 2
```

## 8. Smoke test

```bash
curl -s https://YOUR-RUN-URL/health
```

```bash
curl -s https://YOUR-RUN-URL/v1/ask -H 'Content-Type: application/json' -d '{"subject":"Math","grade":7,"language":"English","tier":"fast","history":[],"question":"How do I divide fractions?"}'
```

Expect `"grounding":"cited"` and a `sources` entry for Prealgebra 2e §4.2. Then check the request's log line:

```bash
gcloud logging read 'resource.type="cloud_run_revision" AND jsonPayload.message="request"' --limit 5 --format json
```

## 9. Point the app at it and retire the old key

In the repo root `.env.local`, set `EXPO_PUBLIC_API_BASE_URL=https://YOUR-RUN-URL` and delete the `EXPO_PUBLIC_GEMMA_API_KEY` line. The app no longer reads it.

That AI Studio key shipped inside v1 builds, so treat it as public. Once local development no longer needs it (step 5 replaces it with Vertex), delete it at aistudio.google.com > API keys.

## Known limits (say these in interviews; don't hide them)

- The endpoint is unauthenticated. The rate limit, `max-instances=2` and the budget alert limit the damage, but none of them is authentication. Firebase App Check or signed-in users would be the real fix.
- The rate limit and request dedup live in memory, so they are per instance and reset on cold start.
- The database password lives in Secret Manager. IAM database authentication would remove the password entirely; the Cloud SQL Python Connector supports it with asyncpg, not psycopg.

## What is actually deployed (Nov 12, 2026)

Project `edureach-api-kb` on the personal Gmail account (no organization), billing account `013784-B92015-FD179C` with the $300 free trial.

| Resource | Setting | Cost |
|---|---|---|
| Cloud Run `edureach-api` | public since Nov 12 (`allUsers` invoker, at Kushal's request; per-device rate limit 20/min), min 0 / max 2 instances, 512 MiB, service account `edureach-api` (Vertex user, Cloud SQL client, log writer, access to one secret) | free tier |
| Cloud SQL `edureach-db` | Postgres 17, `db-f1-micro`, 10 GB HDD, zonal, no backups, no storage auto-increase | about $0.28 per day while running |
| Secret Manager | `edureach-database-url` (read by the service), `edureach-db-password` (used for local ingest) | free tier |
| Artifact Registry | cleanup policy keeps the 2 newest images | under free tier |
| Budget `EduReach hard cap 20 USD` | yearly, **excludes credits** (counts gross usage), emails at 25/50/75/100% | |
| Kill switch `budget-guard` | Cloud Run function on the budget's Pub/Sub topic; at 100% it unlinks billing from the project, which stops everything. Tested Nov 12 with a fake $20 alert: billing turned off within 10 s, then re-linked | free tier |

Budget data lags by hours, so spending can pass $20 slightly before the switch fires. During the free trial, Google can't charge the card unless the account is manually upgraded.

**Making the API public** (done Nov 12). To make it private again, use `remove-iam-policy-binding` with the same arguments:

```bash
gcloud run services add-iam-policy-binding edureach-api --region us-central1 --member allUsers --role roles/run.invoker
```

**Stopping the database between demos** (saves about $0.28 a day; the API keeps answering, marked `grounding: "unavailable"`):

```bash
gcloud sql instances patch edureach-db --activation-policy NEVER
```

```bash
gcloud sql instances patch edureach-db --activation-policy ALWAYS
```

zsh note: write `${P}:us-central1`, not `$P:us-central1`. zsh reads `$P:u` as its uppercase modifier.
