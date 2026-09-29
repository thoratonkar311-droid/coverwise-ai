# CoverWise AI - Production Cloud Deployment Guide

This guide walks you through deploying CoverWise AI using **Render** (FastAPI Backend + PostgreSQL) and **Vercel** (Next.js Frontend). Both platforms offer generous free tiers.

---

## Architecture Overview

```
[User Browser]
       │
       ▼
[Vercel: Next.js Frontend]
  (https://your-app.vercel.app)
       │
       ▼ (API proxy rewrites)
[Render: FastAPI Backend & AI Engine]
  (https://coverwise-backend.onrender.com)
       │
       ▼
[Render / Supabase: PostgreSQL with pgvector]
```

---

## Step 1: Deploy Backend & Database on Render

### Option A: 1-Click Blueprint (Recommended)
1. Go to [render.com](https://render.com) and sign in with your GitHub account.
2. In the Render Dashboard, click **New +** → **Blueprint**.
3. Select your repository: `thoratonkar311-droid/coverwise-ai`.
4. Render will detect the [`render.yaml`](./render.yaml) file automatically:
   - It will provision a free **PostgreSQL Database** (`coverwise-db`).
   - It will build and launch the **FastAPI Web Service** (`coverwise-backend`).
   - It automatically runs database migrations (`alembic upgrade head`).
5. Click **Apply**.
6. Once deployed, copy your Backend URL (e.g., `https://coverwise-backend.onrender.com`).
7. Test the health check endpoint in your browser:
   `https://coverwise-backend.onrender.com/health` (should return `{"status":"ok",...}`).

---

### Option B: Manual Setup on Render

#### 1. Create PostgreSQL Database:
- Click **New +** → **PostgreSQL**.
- Name: `coverwise-db`.
- Database: `coverwise`.
- User: `postgres`.
- Plan: **Free**.
- Once provisioned, copy the **Internal Database URL** (or External if hosting backend elsewhere).

#### 2. Create Web Service:
- Click **New +** → **Web Service**.
- Select repository: `thoratonkar311-droid/coverwise-ai`.
- Runtime: **Python 3**.
- Build Command: `pip install --upgrade pip && pip install -r backend/requirements.txt`
- Start Command: `cd backend && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Plan: **Free**.
- Add Environment Variables:
  - `PYTHONPATH`: `/opt/render/project/src`
  - `ENVIRONMENT`: `production`
  - `SECRET_KEY`: `<generate a random 64-char string>`
  - `ALLOWED_ORIGINS`: `*`
  - `DATABASE_URL`: `<Paste your PostgreSQL Connection String>`
- Click **Create Web Service**.

---

## Step 2: Deploy Frontend on Vercel

1. Go to [vercel.com](https://vercel.com) and sign in with GitHub.
2. Click **Add New...** → **Project**.
3. Select `thoratonkar311-droid/coverwise-ai`.
4. Configure the project:
   - **Framework Preset**: Next.js (detected automatically)
   - **Root Directory**: Click *Edit* and select `frontend`
5. Expand **Environment Variables** and add:
   - `BACKEND_URL`: `https://your-backend-service.onrender.com` (replace with your Render backend URL from Step 1)
   - `NEXT_PUBLIC_API_URL`: (leave blank so Next.js rewrites route traffic through `BACKEND_URL`)
6. Click **Deploy**.
7. Vercel will build your Next.js application and assign a live production URL (e.g., `https://coverwise-ai.vercel.app`).

---

## Step 3: Verification & Smoke Test

Once both are deployed:

1. Open your live Vercel URL in your browser.
2. Check that the Dashboard loads without network errors.
3. Test policy upload or analysis to verify end-to-end communication with the backend.
4. Try the Procedure Cost Simulator to confirm calculation engine results.
5. Use the Coverage Assistant chat to confirm AI responses and citations.

---

## Environment Variables Reference

### Backend
| Variable | Description | Example |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL connection URI | `postgresql://user:pass@host:5432/coverwise` |
| `SECRET_KEY` | JWT authentication key | Random 64-char hex string |
| `ENVIRONMENT` | Runtime environment | `production` |
| `ALLOWED_ORIGINS` | Permitted frontend CORS origins | `https://your-app.vercel.app,http://localhost:3000` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

### Frontend
| Variable | Description | Example |
| :--- | :--- | :--- |
| `BACKEND_URL` | Destination backend API endpoint | `https://coverwise-backend.onrender.com` |
| `NEXT_PUBLIC_API_URL` | Direct client-side API endpoint override | *(optional, leave blank to use proxy)* |
