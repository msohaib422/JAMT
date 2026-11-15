# JAMT — Production Deployment Guide

**JAMT — Junior Astronaut Mission Trainer** is an educational web application that lets
junior astronaut trainees plan and run simulated Moon and Mars missions. It combines a
React single-page frontend, a FastAPI backend, a persistent store for mission state, an
AI Mission Control assistant that answers from **live mission data** and an **official
NASA knowledge base**, and NASA's public live data services (NTRS and PDS).

This guide takes you from a local project to a production deployment using:

| Component | Service |
|-----------|---------|
| Frontend (React + Vite) | Vercel (Project 1) |
| Backend (FastAPI, Python) | Vercel (Project 2) |
| Database (PostgreSQL) | Neon (serverless Postgres) |
| NASA live data + knowledge base | Bundled with the backend, no extra account |
| AI Mission Control | Any OpenAI-compatible LLM API (optional) |

This document is written for beginners. Follow the steps **in order**. Every command and
setting below is based on the actual JAMT codebase — no guessing required.

---

## 1. Project Deployment Overview

### 1.1 What JAMT is

JAMT simulates a full mission lifecycle: mission creation, launch, day-by-day resource
consumption (oxygen, water, food, energy, fuel), astronaut health, emergencies and their
resolution, a mission score/report, and an AI Mission Control chat that can read the live
mission state and answer with official NASA publications as its knowledge source.

### Technologies used

- **Frontend:** React 18, Vite 6, Tailwind CSS, Recharts — in `jamt/`
- **Backend:** FastAPI, SQLAlchemy 2, Pydantic 2, psycopg2 — in `backend/`
- **Local database:** SQLite (`backend/jamt.db`, development only)
- **Production database:** Neon PostgreSQL (persistent; Vercel's filesystem is not)
- **AI/LLM:** OpenAI-compatible `chat/completions` API via `httpx` (optional; a
  deterministic, data-grounded fallback is built in)
- **NASA:** NTRS (NASA Technical Reports Server) and PDS (Planetary Data System) public
  APIs, plus a bundled offline NASA knowledge index with RAG retrieval — no API keys
  required

### 1.2 Production architecture

```
┌────────────────────┐          HTTPS          ┌────────────────────┐
│  Vercel Project 1  │  ────────────────────▶  │  Vercel Project 2  │
│  JAMT Frontend     │   VITE_API_BASE_URL     │  JAMT Backend      │
│  (React + Vite)    │                         │  (FastAPI)         │
│  jamt/             │                         │  backend/          │
└────────────────────┘                         └─────────┬──────────┘
                                                         │ SQLAlchemy
                                              ┌──────────▼──────────┐
                                              │  Neon PostgreSQL    │
                                              │  (pooled endpoint)  │
                                              └─────────────────────┘
                                                         │
                                        BACKEND_API_URL  │  (agent calls its own API)
                                                         ▼
                                              ┌─────────────────────┐
                                              │ /api/agent/chat     │
                                              │ LLM (optional)      │
                                              │ NASA RAG + live NTRS│
                                              │ / PDS (no keys)     │
                                              └─────────────────────┘
```

### 1.3 Why two Vercel projects

The frontend is a static Vite build (HTML/CSS/JS), while the backend is a Python
serverless application. Vercel treats them as two different frameworks, and each project
needs its own root directory, build settings, and environment variables. Deploying them
as **two projects from the same GitHub repository** keeps the code together while giving
each side the correct runtime:

| | Project 1 — Frontend | Project 2 — Backend |
|---|---|---|
| Root Directory | `jamt/` | `backend/` |
| Framework | Vite (auto-detected) | Python / FastAPI (auto-detected) |
| Build Command | `npm run build` | *(none — Vercel installs `requirements.txt`)* |
| Output Directory | `dist` | *(not applicable)* |
| Entry Point | `index.html` | `app/main.py` (exposes `app = FastAPI()`) |
| Key environment variable | `VITE_API_BASE_URL` | `JAMT_DATABASE_URL`, `BACKEND_API_URL`, … |

**Deploy the backend first**, obtain its URL, then set the frontend's `VITE_API_BASE_URL`
and the backend's `BACKEND_API_URL` to the real URLs.

---

## 2. Deployment Prerequisites

### 2.1 Accounts

1. **GitHub** — the repository will be pushed here and connected to Vercel.
   [github.com](https://github.com)
2. **Vercel** — free Hobby plan is fine. Sign up with your GitHub account at
   [vercel.com](https://vercel.com).
3. **Neon** — free serverless PostgreSQL. [neon.tech](https://neon.tech)
   (No credit card required for the free tier.)

### 2.2 Tools on your machine

| Tool | Version | Check |
|------|---------|-------|
| Git | any recent | `git --version` |
| Node.js | 18 or newer (20 LTS / 22 LTS recommended) | `node --version` |
| npm | bundled with Node | `npm --version` |
| Python | 3.10 or newer (3.12 recommended) | `python3 --version` |
| pip | bundled with Python | `pip3 --version` |

> The backend was verified on Python 3.14 locally; Vercel deploys FastAPI with its
> supported Python runtime (Python 3.12 at the time of writing) automatically. No Python
> version configuration is required.

### 2.3 API credentials (optional)

| Credential | Required? | Used for |
|------------|-----------|----------|
| `LLM_API_KEY` (or `OPENROUTER_API_KEY`) | **Optional** | LLM-written AI Mission Control answers. Without it, JAMT still answers using live mission data + NASA knowledge with a deterministic, non-AI fallback. |
| `NASA_API_KEY` | **Not used** | NTRS and PDS are public services and need no key. The variable exists only for future NASA APIs. |
| `TAVILY_API_KEY` | **Optional** | Reserved web-search integration; not required by the current code paths. |

No credential is needed to deploy or to use the core application.

---

## 3. Project Preparation

### 3.1 Repository structure

```
.                          ← repository root
├── DEPLOYMENT.md          ← this document
├── .gitignore             ← keeps secrets, databases and build output out of git
├── backend/               ← Vercel Project 2 (FastAPI)
│   ├── app/
│   │   ├── main.py        ← FastAPI app (entry point: exposes `app`)
│   │   ├── ai/            ← agent orchestration, tools, config, bundled NASA knowledge
│   │   │   └── data/nasa_knowledge.json   ← offline RAG index (committed, ~9 MB)
│   │   ├── nasa/          ← NTRS / PDS clients and TTL cache
│   │   └── …
│   ├── requirements.txt   ← Python dependencies (Vercel installs this)
│   ├── .env.example       ← template for backend environment variables
│   ├── jamt.db            ← LOCAL SQLite file — never commit, never deploy as data
│   └── tests/
├── jamt/                  ← Vercel Project 1 (React + Vite)
│   ├── src/
│   │   └── services/api.js   ← reads VITE_API_BASE_URL
│   ├── package.json
│   ├── vite.config.js
│   ├── .env.example       ← template for frontend environment variables
│   └── dist/              ← build output — never commit (rebuilt by Vercel)
```

### 3.2 Files that must NOT be committed

The root `.gitignore` (already present) excludes them:

- `.env` files anywhere (real credentials) — `.env.example` **is** committed on purpose
- `node_modules/`
- `dist/` (frontend build output)
- `*.db` / `*.sqlite3` (local SQLite — including `backend/jamt.db`)
- `__pycache__/`, `.pytest_cache/`
- `cache/`, `chroma_db/` (generated caches)
- `.vercel/`

**Local SQLite is development-only.** The production backend persists data in Neon.
The application never relies on the SQLite file in production, and deleting or
recreating it is never required — leave `backend/jamt.db` alone.

### 3.3 Environment file preparation (local)

```bash
# Frontend — optional locally; the app falls back to http://127.0.0.1:8000
cp jamt/.env.example jamt/.env

# Backend — optional locally; defaults to sqlite:///./jamt.db
cp backend/.env.example backend/.env
```

Edit only the values you need. The committed templates use placeholders — **never paste
real keys into `.env.example`.**

### 3.4 Push the project to GitHub

If the folder is not a git repository yet:

```bash
cd "/path/to/Frontend Update"
git init
git add .
git status                 # sanity check — no .env, no *.db, no node_modules
git commit -m "Prepare JAMT for Vercel deployment"
```

Create an empty repository on GitHub (no README, no .gitignore — we have our own), then:

```bash
git branch -M main
git remote add origin https://github.com/<your-user>/<your-repo>.git
git push -u origin main
```

> If `git status` lists `backend/jamt.db` or any `.env`, stop and re-check `.gitignore`.

---

## 4. Neon PostgreSQL Setup

The production backend stores **all** missions, astronauts, emergencies and events in
Neon. Vercel's filesystem is ephemeral and read-only outside `/tmp`, so a SQLite file on
Vercel would lose data — Neon is the persistent store.

### 4.1 Create a Neon account and project

1. Go to [console.neon.tech](https://console.neon.tech) and sign up (GitHub sign-in works).
2. Click **New Project**.
3. **Project name:** `jamt` (any name works).
4. **Postgres version:** keep the default (16 or newer).
5. **Region:** choose the region closest to your Vercel functions (e.g. `AWS / US East
   (N. Virginia) - us-east-1`).
6. Click **Create project**.

### 4.2 Create/select a database

A fresh project creates one database automatically (usually `neondb`). That is all you
need — JAMT creates its tables automatically on first startup. You do **not** need to
create any tables manually, and you must **not** paste table-creation SQL yourself.

If you want a dedicated database: in the Neon dashboard, open the **SQL Editor** and run:

```sql
CREATE DATABASE jamt;
```

(Using the default `neondb` is equally fine.)

### 4.3 Get the pooled connection string

1. In the Neon dashboard, open your project.
2. Click **Dashboard** (or use the **Connection Details** panel on the overview page).
3. Under **Connection string**, select the **Pooled connection** toggle/endpoint
   (host contains `-pooler`, e.g. `ep-cool-name-pooler.us-east-1.aws.neon.tech`).
   Use the pooled endpoint — serverless functions open many short-lived connections.
4. Select the branch (`main`), the database (e.g. `neondb`), and copy the string. It
   looks like:

   ```
   postgresql://USER:PASSWORD@ep-cool-name-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require
   ```

5. The `?sslmode=require` suffix is **mandatory** — Neon only accepts TLS connections.
   Keep it exactly as shown.

> Keep this string secret. It contains the database password. Treat it like a password:
> never commit it, never paste it into chat/issues, rotate it if it leaks.

### 4.4 Configure `JAMT_DATABASE_URL`

This value is used in **one** place: Vercel Project 2 → Settings → Environment Variables
(see [Section 5](#5-deploy-backend-to-vercel)). Example (placeholder):

```
JAMT_DATABASE_URL=postgresql://USER:PASSWORD@ep-cool-name-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require
```

Notes:

- Both `postgres://` and `postgresql://` URLs work; the backend normalises them
  automatically and pins the `psycopg2` driver (which `requirements.txt` installs).
- Do not add quotes around the value in the Vercel dashboard.
- Neon's autoscaling and scale-to-zero are compatible with the backend: connections are
  checked before use (`pool_pre_ping`) and recycled every 5 minutes.
- The backend creates missing tables (`missions`, `astronauts`, `emergencies`,
  `mission_events`) automatically on first request via SQLAlchemy `create_all()`.
  This is **safe and idempotent** — it never drops or modifies existing rows and is not
  a migration tool. If you later change the data models, adopt a real migration tool
  (e.g. Alembic) instead of relying on `create_all()`.

### 4.5 Keep credentials secure

- Store the connection string only in Vercel's Environment Variables (encrypted at rest)
  and in your local `backend/.env` (git-ignored).
- Never commit it; never expose it in the frontend — the frontend talks only to the
  backend.
- In Neon → **Settings → Roles**, you can reset the password if needed; then update the
  Vercel variable and redeploy.

---

## 5. Deploy Backend to Vercel

### 5.1 Import the repository

1. Sign in to [vercel.com](https://vercel.com) → **Add New… → Project**.
2. Under **Import Git Repository**, choose **GitHub** and authorise Vercel to read your
   repository if prompted.
3. Find `<your-user>/<your-repo>` and click **Import**.

### 5.2 Configure the project

| Setting | Value |
|---------|-------|
| **Project Name** | `jamt-backend` (any unique name; the public URL becomes `https://jamt-backend.vercel.app`) |
| **Framework Preset** | Leave as detected — Vercel detects the Python/FastAPI app from `requirements.txt` and `app/main.py` (it looks for `app = FastAPI()` at module level, which `backend/app/main.py` provides) |
| **Root Directory** | Click **Edit** and select **`backend`** ← **this is the critical step** |
| **Build Command** | *(leave empty — nothing to build)* |
| **Output Directory** | *(leave empty)* |
| **Install Command** | *(leave default — Vercel runs `pip install -r requirements.txt`)* |

> No `vercel.json` or any other configuration file is required. The backend ships
> everything Vercel needs: `requirements.txt` (including `psycopg2-binary`) and
> `app/main.py` exposing the ASGI `app` object. Do **not** add a custom runtime.

### 5.3 Add backend environment variables

Before clicking **Deploy**, expand **Environment Variables** and add the following.
(You can also add them later under **Settings → Environment Variables** — see §5.6.)

| Name | Value | Environment |
|------|-------|-------------|
| `JAMT_DATABASE_URL` | pooled Neon string from §4.3, e.g. `postgresql://USER:PASSWORD@…-pooler.…aws.neon.tech/neondb?sslmode=require` | Production (and Preview if desired) |
| `BACKEND_API_URL` | `https://jamt-backend.vercel.app` (your planned backend URL — see note below) | Production |
| `NASA_DATA_ENABLED` | `true` | All |
| `NASA_CACHE_DIRECTORY` | `/tmp/jamt-nasa-cache` *(optional — this is the automatic default on Vercel)* | Production |
| `NASA_DATA_CACHE_TTL` | `86400` *(optional)* | All |

Optional AI variables (choose one provider block; both can be left unset):

| Name | Example | Purpose |
|------|---------|---------|
| `LLM_API_KEY` | `nvapi-…` | API key for your LLM provider (NVIDIA NIM / OpenRouter-compatible) |
| `LLM_MODEL` | `nvidia/nemotron-3-ultra-550b-a55b` | Model id |
| `LLM_BASE_URL` | `https://integrate.api.nvidia.com/v1` | OpenAI-compatible endpoint |
| `LLM_TIMEOUT_SECONDS` | `45` | Request timeout |
| `LLM_MAX_TOKENS` | `800` | Max answer tokens |
| `LLM_TEMPERATURE` | `0.2` | Deterministic answers |

> **About `BACKEND_API_URL`:** the AI agent calls the backend's own HTTP API to read
> live mission data (it never reads the database directly). Set it to the backend's
> public URL. If you know the project name in advance (`jamt-backend`), the URL
> `https://jamt-backend.vercel.app` is predictable and can be set before the first
> deploy. If not, deploy first, copy the real URL from the deployment page, set the
> variable, and **redeploy** (§11.3) — environment variable changes only apply to new
> deployments.

> **About `NASA_CACHE_DIRECTORY`:** on Vercel the filesystem outside `/tmp` is read-only,
> so the backend automatically defaults its NASA cache to `/tmp/jamt-nasa-cache` when it
> detects the Vercel environment (`VERCEL`/`VERCEL_ENV` is set by the platform). You only
> need to set this variable if you want a different location. Cache contents are
> ephemeral — NASA data is re-fetched or served stale-labelled from `/tmp` as needed.

### 5.4 Deploy

Click **Deploy**. Vercel will:

1. Clone your repository,
2. Install Python packages from `backend/requirements.txt`,
3. Package the FastAPI app from `backend/app/main.py` as a serverless function,
4. Assign the domain `https://<project-name>.vercel.app`.

Watch the build log. A healthy log shows the pip install completing and
`✓ Deployment completed` — there is no compile step for Python.

> The 9 MB bundled NASA knowledge index (`app/ai/data/nasa_knowledge.json`) is part of
> the deployment and works read-only. No database migrations need to run.

### 5.5 Obtain the backend URL and test `/health`

1. Open the deployment → **Domains** (or the top of the deployment page):
   `https://jamt-backend.vercel.app` (replace with yours).
2. Test health in a browser or terminal:

   ```bash
   curl https://jamt-backend.vercel.app/health
   # {"status":"ok"}

   curl https://jamt-backend.vercel.app/api/health
   # {"status":"ok"}
   ```

3. Test the NASA integration (no keys needed):

   ```bash
   curl https://jamt-backend.vercel.app/api/nasa/status
   ```

4. If you set `BACKEND_API_URL` only after the first deploy, now run **Deployments →
   ⋯ → Redeploy** on the backend so the agent can reach the API.

### 5.6 Updating environment variables later

**Settings → Environment Variables** → edit/add → then **Deployments → ⋯ → Redeploy**.
Variables are baked in at deployment time; the redeploy is required.

---

## 6. Deploy Frontend to Vercel

### 6.1 Import the same repository again

1. **Add New… → Project**.
2. Import the **same** GitHub repository.
3. **Project Name:** `jamt-frontend` (public URL becomes `https://jamt-frontend.vercel.app`).

### 6.2 Configure the project

| Setting | Value |
|---------|-------|
| **Root Directory** | Click **Edit** and select **`jamt`** |
| **Framework Preset** | `Vite` (auto-detected from `package.json` and `vite.config.js`) |
| **Build Command** | `npm run build` (default for Vite) |
| **Output Directory** | `dist` (default for Vite; matches `jamt/vite.config.js`) |
| **Install Command** | *(default — `npm install`)* |

### 6.3 Set `VITE_API_BASE_URL`

Expand **Environment Variables** and add:

| Name | Value | Environment |
|------|-------|-------------|
| `VITE_API_BASE_URL` | `https://jamt-backend.vercel.app` (your backend URL from §5.5 — **no trailing slash**) | Production (and Preview if desired) |

> Vite **inlines** `VITE_API_BASE_URL` into the JavaScript bundle at **build time**.
> Changing this variable later requires a redeploy of the frontend to take effect.
> Local development needs nothing: without the variable, the app falls back to
> `http://127.0.0.1:8000`.

### 6.4 Deploy

Click **Deploy**. Vercel installs dependencies, runs `npm run build`, and publishes
`dist/` to a CDN. When finished, the deployment page shows
`https://jamt-frontend.vercel.app`.

### 6.5 Verify

Open `https://jamt-frontend.vercel.app` — the JAMT landing page loads. Create a mission;
it should persist (refresh the page — the mission history is still there, now stored in
Neon).

---

## 7. Environment Variables Reference

### 7.1 Frontend (Vercel Project 1 — `jamt/`)

| Variable | Required? | Purpose | Example |
|----------|-----------|---------|---------|
| `VITE_API_BASE_URL` | **Production: yes.** Local: optional (defaults to `http://127.0.0.1:8000`) | Base URL the frontend uses for every API call (`src/services/api.js`). Inlined at build time. Trailing slash is stripped automatically. | `https://jamt-backend.vercel.app` |

### 7.2 Backend (Vercel Project 2 — `backend/`)

| Variable | Required? | Purpose | Example |
|----------|-----------|---------|---------|
| `JAMT_DATABASE_URL` | **Production: yes.** Local: optional (defaults to `sqlite:///./jamt.db`) | SQLAlchemy connection string. `sqlite*` → SQLite with `check_same_thread=False`; anything else → PostgreSQL with `pool_pre_ping` + `pool_recycle=300`. `postgres://` is normalised to `postgresql://` and pinned to the `psycopg2` driver. | `postgresql://USER:PASSWORD@ep-…-pooler.…aws.neon.tech/neondb?sslmode=require` |
| `BACKEND_API_URL` | **Production: yes** (required for the AI agent to read live mission data). Local: optional (default `http://127.0.0.1:8000`) | Base URL the AI agent tools use to call this backend's own HTTP API. | `https://jamt-backend.vercel.app` |
| `NASA_DATA_ENABLED` | Optional (default `true`) | Master switch for live NASA data (NTRS/PDS) and the NASA sections of the agent. Set `false` to disable. | `true` |
| `NASA_CACHE_DIRECTORY` | Optional (default `./cache/nasa` locally; `/tmp/jamt-nasa-cache` automatically on Vercel) | Where NASA API responses are cached (TTL `NASA_DATA_CACHE_TTL`). Must be writable — hence `/tmp` on Vercel. | `/tmp/jamt-nasa-cache` |
| `NASA_DATA_CACHE_TTL` | Optional (default `86400`) | Cache lifetime in seconds for NASA responses. | `86400` |
| `NASA_NTRS_API_BASE_URL` | Optional | Override NTRS base URL. | `https://ntrs.nasa.gov/api` |
| `NASA_PDS_API_BASE_URL` | Optional | Override PDS base URL. | `https://pds.nasa.gov/api/search/1` |
| `NASA_API_KEY` | Optional (unused) | Reserved — NTRS/PDS are public; no key required today. | *(empty)* |
| `LLM_API_KEY` | Optional | API key for the LLM used by AI Mission Control. Falls back to `OPENROUTER_API_KEY` if unset. | `nvapi-…` or `sk-or-…` |
| `LLM_MODEL` | Optional (default `openai/gpt-4o-mini`, or `OPENROUTER_MODEL`) | Model identifier sent to the provider. | `nvidia/nemotron-3-ultra-550b-a55b` |
| `LLM_BASE_URL` | Optional (default `https://openrouter.ai/api/v1`, or `OPENROUTER_BASE_URL`) | OpenAI-compatible base URL. | `https://integrate.api.nvidia.com/v1` |
| `LLM_TIMEOUT_SECONDS` | Optional (default `45`) | LLM request timeout. | `45` |
| `LLM_MAX_TOKENS` | Optional (default `800`) | Max completion tokens. | `800` |
| `LLM_TEMPERATURE` | Optional (default `0.2`) | Sampling temperature. | `0.2` |
| `OPENROUTER_API_KEY` | Optional | Legacy/provider-specific alias for `LLM_API_KEY`. | `sk-or-…` |
| `OPENROUTER_MODEL` | Optional (default `openai/gpt-4o-mini`) | Legacy/provider-specific alias for `LLM_MODEL`. | `openai/gpt-4o-mini` |
| `OPENROUTER_BASE_URL` | Optional (default `https://openrouter.ai/api/v1`) | Legacy/provider-specific alias for `LLM_BASE_URL`. | `https://openrouter.ai/api/v1` |
| `CHROMA_PERSIST_DIRECTORY` | Optional (default `./chroma_db`) | Optional ChromaDB persistence for semantic RAG; keyword fallback works without it. | `./chroma_db` |
| `EMBEDDING_MODEL` | Optional (default `sentence-transformers/all-MiniLM-L6-v2`) | Embedding model for optional semantic RAG. | `sentence-transformers/all-MiniLM-L6-v2` |
| `TAVILY_API_KEY` | Optional | Reserved web-search integration; not used by current code paths. | `tvly-…` |
| `JAMT_SKIP_DB_INIT` | Optional (test-only) | `1`/`true`/`yes` disables schema creation on import. Set automatically by the test suite. | *(unset in production)* |
| `JAMT_LIVE_TESTS` | Optional (test-only) | `1` enables live NASA connectivity tests in the test suite. | *(unset in production)* |
| `VERCEL` / `VERCEL_ENV` | Platform-provided | Set by Vercel automatically; the backend uses them to default the NASA cache to `/tmp`. Do not set manually. | *(injected)* |

> **Never** put any of these in the frontend project, and never commit real values.
> `.env.example` files in the repo contain placeholders only.

---

## 8. Post-Deployment Verification

Work through this checklist in order. Replace `BACKEND` with your backend URL and
`FRONTEND` with your frontend URL.

### 8.1 Backend smoke tests (browser or curl)

- [ ] `curl BACKEND/health` → `{"status":"ok"}`
- [ ] `curl BACKEND/api/health` → `{"status":"ok"}`
- [ ] `curl BACKEND/api/nasa/status` → JSON with `"enabled": true` and indexed document counts (14 documents, 4000+ chunks)
- [ ] `curl BACKEND/api/nasa/sources` → list of 14 official NTRS publications with provenance
- [ ] `curl BACKEND/api/config/simulation` → destinations/difficulties/consumption profile JSON

### 8.2 Frontend + database (browser, on `FRONTEND`)

- [ ] Landing page loads without errors (open DevTools → Console; no red errors).
- [ ] **Mission creation** — create a mission (Easy, Moon/Mars, 1–3 astronauts). It appears in mission history.
- [ ] **Persistence** — refresh the page / reopen the browser; the mission is still listed (this proves Neon is the store).
- [ ] **Mission start** — press Start on a draft mission.
- [ ] **Pause / Resume** — pause and resume the mission; status badge changes correctly.
- [ ] **Advance Day** — advance several days; progress increases.
- [ ] **Resource consumption** — oxygen/water/food/energy/fuel decrease over days per the shown consumption plan.
- [ ] **Astronaut health** — health decreases over days; status chips update (Good/Watch Out/Critical).
- [ ] **Emergency trigger** — trigger an emergency; modal appears and effects apply.
- [ ] **Emergency resolution** — execute the hinted action (e.g. Repair), then Resolve; emergency clears.
- [ ] **Mission report** — open the report/Training Report modal; score, metrics and feedback render.
- [ ] **Leaderboard/history** — mission history modal lists events.

### 8.3 AI Mission Control (browser)

- [ ] Open AI Mission Control; ask "What is the current status of my mission?" — answer reflects live day/resources (the agent reads them via `BACKEND_API_URL`).
- [ ] Ask a NASA question, e.g. "What does NASA say about water recycling?" — answer cites NTRS document ids (e.g. `[20210024855]`) and sources are listed.
- [ ] Without `LLM_API_KEY`, answers are deterministic and data-grounded (expected). With an LLM key configured, answers are natural-language but still grounded in live data and NASA passages.

### 8.4 NASA live data (curl)

- [ ] `curl "BACKEND/api/nasa/datasets?destination=moon&limit=3"` → `"available": true` with Apollo-era PDS bundles.
- [ ] `curl "BACKEND/api/nasa/reports?q=space%20suit&limit=2"` → `"available": true` with NTRS hits.
- [ ] If NASA is unreachable, the API answers `"available": false` with a message — never fabricated data — and the app keeps working offline from the bundled knowledge base.

### 8.5 Command-line sanity check (optional)

```bash
# List missions (empty array is fine on a fresh deployment)
curl BACKEND/api/missions

# Simulation config
curl BACKEND/api/config/simulation | head -c 200
```

---

## 9. Common Deployment Errors

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| **500 Internal Server Error** on every backend route | Database unreachable or bad `JAMT_DATABASE_URL` | Check the variable in **Settings → Environment Variables**; ensure the pooled host, `sslmode=require`, correct user/password/database; check **Deployments → ⋯ → View Function Logs**. |
| **Database connection failure** at startup / first request | Wrong password, non-pooled endpoint, or password with special characters not URL-encoded | Re-copy the pooled string from Neon; URL-encode special characters in the password (e.g. `@` → `%40`); keep `?sslmode=require`. |
| **psycopg2 / PostgreSQL driver errors** (`ModuleNotFoundError`, `no module named 'psycopg2'`) | `requirements.txt` not installed or wrong driver pinned | The backend requirements include `psycopg2-binary>=2.9.9`; plain `postgresql://` URLs are pinned to `psycopg2` automatically by `app/main.py`. If you override `JAMT_DATABASE_URL` with `postgresql+psycopg2://…`, that is fine. Do **not** delete `psycopg2-binary` from requirements. |
| **`value out of range for type integer`** on mission creation | 32-bit INTEGER id column vs. 64-bit mission ids | Fixed in this codebase (`BigInteger`). If you see it on your own fork, make sure `missions.id` and the `mission_id` foreign keys are `BigInteger`. |
| **Environment variable errors** (empty LLM replies, agent can't see mission data) | Variable set but not redeployed, or `BACKEND_API_URL` points at localhost | Vite and backend env vars are baked in at build/deploy time — **redeploy** after every change. `BACKEND_API_URL` must be the **public** backend URL, never `http://127.0.0.1:8000` on Vercel. |
| **CORS errors** in the browser console | Should not happen — backend allows any origin (`allow_origin_regex=".*"` with credentials) | If you hardened CORS, add your frontend origin (`https://jamt-frontend.vercel.app`) to `allow_origins` in `backend/app/main.py` and redeploy the backend. No credentials-bearing wildcard secrets are involved. |
| **Frontend API connection errors** / missions don't load | `VITE_API_BASE_URL` missing, wrong, or still `http://127.0.0.1:8000` | Set `VITE_API_BASE_URL=https://jamt-backend.vercel.app` in Project 1 → Settings → Environment Variables; redeploy the frontend (Vite inlines at build time). Check the Network tab: requests should go to the backend domain. |
| **Python runtime errors** | Very old pins or unsupported runtime | Use `requirements.txt` as shipped; do not add a `runtime.txt`. Vercel uses its supported Python 3.x automatically. If a build log mentions a missing package, re-check you did not delete a line from `requirements.txt`. |
| **Vercel function timeout** | LLM or NASA request slower than the plan's limit | Hobby plan functions cap at ~10–60 s; `LLM_TIMEOUT_SECONDS=45` fits within that. Reduce `LLM_TIMEOUT_SECONDS` if needed. NASA calls have internal timeouts and never hang indefinitely; on failure they return `available: false`. |
| **`@vercel/python` … no such file or directory** / zero functions found | Wrong Root Directory (repo root instead of `backend/`) | Project 2 → Settings → **Root Directory** must be `backend`, and Project 1 → `jamt`. |
| **`/tmp` right or cache errors on Vercel** | `NASA_CACHE_DIRECTORY` pointed at a read-only path | Unset it (defaults to `/tmp/jamt-nasa-cache` on Vercel) or set it to a `/tmp/…` path. |
| **NASA API failures** (`available: false`) | NASA services rate-limit or are down | Expected and handled honestly — the app keeps working; cached copies are labelled `cached: true` / served stale when offline. Retry later; do not remove the integration. |
| **AI API authentication failures** (deterministic answers instead of LLM) | Wrong/expired `LLM_API_KEY` | Check the key with your provider; check `LLM_BASE_URL`; watch backend logs (`LLM request failed: status=401/429`). The app still functions via the built-in fallback. |
| **Empty serverless response / 404 on routes** | Wrong entrypoint detection | Do not rename `app/main.py` or the `app` variable; do not add a `vercel.json`. Routes are served relative to the domain root: `BACKEND/health`, `BACKEND/api/missions`, … |
| **`better-sqlite3` / native module errors** | N/A — this project has no native npm modules | If Vercel misdetects the backend as a Node project (a stray empty `package-lock.json` in `backend/` can confuse detection), delete `backend/package-lock.json`, commit, and let Vercel re-detect Python. The frontend (`jamt/`) keeps its real `package.json`. |

---

## 10. Local Development After Deployment

Your local setup keeps working exactly as before — Vercel and Neon are only used for
production.

### 10.1 Run the backend locally (SQLite)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate    # optional but recommended
pip install -r requirements.txt
cp .env.example .env                                   # optional; defaults work
uvicorn app.main:app --reload --port 8000
```

- Uses `./jamt.db` (SQLite) by default — your existing local data is untouched.
- Test: `curl http://127.0.0.1:8000/health` → `{"status":"ok"}`

### 10.2 Run the frontend locally

```bash
cd jamt
npm install
npm run dev        # http://localhost:5173 (Vite)
```

- Without any env file it calls `http://127.0.0.1:8000` (the fallback in
  `src/services/api.js`) — zero configuration needed.
- Or copy `.env.example` to `.env` and edit `VITE_API_BASE_URL` (e.g. to your Neon-backed
  backend) if you want local UI against production data (not recommended for write tests).

### 10.3 Run the backend test suite

```bash
cd backend
python -m pytest                 # offline; in-memory SQLite, never touches jamt.db
JAMT_LIVE_TESTS=1 python -m pytest tests/test_nasa.py   # opt-in: live NASA calls
```

The suite sets `JAMT_SKIP_DB_INIT=1` and `JAMT_DATABASE_URL=sqlite://` (in-memory) via
`conftest.py`. Known pre-existing failure: `tests/test_jamt_workflow.py::TestMissionLifecycle::test_complete_mars_workflow` expects `"Astronaut 1"` while the application seeds preset crew names (`Alex Carter`, …). It fails the same way on the unmodified codebase and is unrelated to deployment; it was left untouched deliberately.

### 10.4 Reset local data (development only)

Delete `backend/jamt.db` to start fresh — it is recreated automatically on next startup.
**Never** do this against production, and never delete the Neon database to "fix" a deploy.

---

## 11. Redeployment & Maintenance

### 11.1 Automatic deployments

Both Vercel projects are connected to the same repository. Every push to `main`
triggers a new deployment of both projects.

- Push to any branch → Vercel creates a **Preview** deployment for both projects.
- Merge/push to `main` → **Production** deployment for both projects.

### 11.2 Manual redeploy

Vercel Dashboard → Project → **Deployments** → ⋯ on the latest deployment →
**Redeploy**. Use this after changing environment variables or if a deploy needs a rebuild.

### 11.3 Update environment variables

**Settings → Environment Variables** → edit → save → redeploy (required for changes to
take effect). For Vite variables, the redeploy rebuilds the bundle with the new value.

### 11.4 Logs and monitoring

- **Function logs:** Project → **Deployments** → latest → **Functions** / **Logs**, or
  **Runtime Logs** (real-time). Watch for `LLM request failed`, `NASA source error`, or
  SQLAlchemy pool warnings.
- **Build logs:** failed deployments show the exact pip/npm error; fix and push again.
- **Neon monitoring:** Neon Dashboard → **Monitoring** shows connections, storage and
  query activity. The free tier has generous limits; watch storage growth from mission
  events.
- **Health check:** `GET /health` (and `/api/health`) return `{"status":"ok"}` — point an
  uptime monitor (e.g. UptimeRobot, Better Stack free tier) at it. NASA endpoints and the
  frontend are naturally exercised by user traffic; there are no background jobs.

### 11.5 Database backup

Neon point-in-time restore and branching are your safety net:

1. Neon Dashboard → **Branches** → **Create branch** (e.g. `backup-2026-11-15`) — instant copy.
2. Or use **pg_dump** locally:
   ```bash
   pg_dump "<pooled-connection-string>" > jamt-backup.sql
   ```
3. Neon also supports scheduled `pg_dump` via cron to any storage you control.

Restore: create a new branch/database from the backup and point `JAMT_DATABASE_URL` at it, redeploy.

### 11.6 Keeping NASA knowledge fresh (optional)

The bundled knowledge index ships with the repo (`backend/app/ai/data/nasa_knowledge.json`).
Re-running the ingestion scripts (`backend/scripts/ingest_nasa_documents.py`) updates it;
commit the result and push — Vercel redeploys automatically. The live NTRS/PDS caches in
`/tmp` are ephemeral and refresh themselves (TTL `NASA_DATA_CACHE_TTL`, default 24 h).

---

## 12. Final Deployment Checklist

### Repository
- [ ] `.gitignore` present; `git status` shows no `.env`, `*.db`, `node_modules/`, `dist/`
- [ ] `backend/.env.example` and `jamt/.env.example` contain placeholders only
- [ ] Repository pushed to GitHub (`main`)

### Neon
- [ ] Neon project created; region matches Vercel functions
- [ ] Pooled connection string copied (host contains `-pooler`, `?sslmode=require`)
- [ ] `JAMT_DATABASE_URL` added to Vercel Project 2 (Production) — value kept secret

### Backend (Vercel Project 2 — root `backend/`)
- [ ] Root Directory = `backend/`; Framework = Python/FastAPI (auto)
- [ ] Environment variables: `JAMT_DATABASE_URL`, `BACKEND_API_URL`, `NASA_DATA_ENABLED=true` (+ optional `NASA_CACHE_DIRECTORY=/tmp/jamt-nasa-cache`, LLM vars)
- [ ] First deploy succeeded; `BACKEND_API_URL` set to the real backend URL; redeployed
- [ ] `curl BACKEND/health` → `{"status":"ok"}`
- [ ] `curl BACKEND/api/nasa/status` → `enabled: true`

### Frontend (Vercel Project 1 — root `jamt/`)
- [ ] Root Directory = `jamt/`; Framework = Vite; Build `npm run build`; Output `dist`
- [ ] `VITE_API_BASE_URL=https://<your-backend>.vercel.app` (no trailing slash), then redeploy
- [ ] Landing page opens with no console errors

### Functional verification (browser)
- [ ] Mission created → refresh → mission persists (Neon working)
- [ ] Start → advance days → resources decrease → health decays
- [ ] Pause/resume works
- [ ] Emergency trigger → action → resolve works
- [ ] Mission report renders (score + feedback)
- [ ] AI Mission Control answers with live mission data (tools_used populated in the response)
- [ ] NASA question cites NTRS ids; `/api/nasa/datasets` and `/api/nasa/reports` return `available: true`

### Ongoing
- [ ] Uptime monitor on `BACKEND/health`
- [ ] Neon branch backup taken before risky changes
- [ ] Push to `main` redeploys both projects; verify after each push

---

## Appendix A — Two-project summary (copy/paste)

```
Backend project
  Root Directory : backend
  Framework      : Python / FastAPI (auto-detected)
  Entry point    : app/main.py  (exposes `app`)
  Install        : pip install -r requirements.txt   (incl. psycopg2-binary)
  Env            : JAMT_DATABASE_URL (Neon pooled, sslmode=require)
                   BACKEND_API_URL   (this backend's public URL)
                   NASA_DATA_ENABLED=true
                   NASA_CACHE_DIRECTORY=/tmp/jamt-nasa-cache  (or unset)
                   LLM_API_KEY / LLM_MODEL / LLM_BASE_URL …   (optional)

Frontend project
  Root Directory : jamt
  Framework      : Vite
  Build          : npm run build
  Output         : dist
  Env            : VITE_API_BASE_URL=https://<backend>.vercel.app
```

## Appendix B — What is NOT required

- No Docker, no VPS, no separate backend host.
- No `vercel.json`, no serverless-function scaffolding — zero config by design.
- No changes to the simulation, NASA knowledge data, or UI.
- No database migration on first deploy — tables are created automatically and idempotently.
- No NASA API keys. NTRS and PDS are public.
- No LLM key — the built-in deterministic, data-grounded assistant works without one.
