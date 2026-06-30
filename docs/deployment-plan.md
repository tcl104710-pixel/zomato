# Zomato AI Recommender - Deployment Plan

This document outlines the deployment strategy for separating the full-stack repository into a **Vercel-hosted Frontend** and a **Railway-hosted Backend**.

## Architecture Overview

1. **Frontend (Vercel)**: Hosts the static HTML, CSS, and Vanilla JS files. Vercel's global CDN ensures fast load times for the UI.
2. **Backend API (Railway)**: Hosts the FastAPI Python application, which processes requests, loads the Zomato CSV dataset into memory, and handles communication with the Groq LLM API.

---

## 1. Preparing the Codebase for Split Deployment

Since the frontend and backend are currently in the same repository and the frontend relies on `window.location.origin` for API calls, we need to make a small code change to support separate domains.

### Update Frontend API Call
In `frontend/scripts/app.js`, update the `API_BASE` constant to use an environment variable (if using a build step) or fallback to a hardcoded Railway URL for production.

**Change this:**
```javascript
const API_BASE = window.location.origin;
```

**To this:**
```javascript
// Automatically use current origin in local dev, but use Railway URL in production
const IS_PROD = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1';
const API_BASE = IS_PROD 
    ? 'https://your-railway-app-name.up.railway.app' 
    : window.location.origin;
```
*(Note: You will replace `your-railway-app-name.up.railway.app` with the actual URL provided by Railway once deployed).*

---

## 2. Deploying the Backend to Railway

Railway natively supports Python and FastAPI. It will look for your `requirements.txt` to install dependencies.

### Steps:
1. **Create an Account**: Sign up at [Railway.app](https://railway.app/) and link your GitHub account.
2. **New Project**: Click **New Project** -> **Deploy from GitHub repo** -> Select the `tcl104710-pixel/zomato` repository.
3. **Configure the Service**:
   - Railway will automatically detect the Python environment.
   - Go to the **Variables** tab for the newly created service and add your environment variables:
     - `GROQ_API_KEY` = `your-api-key-here`
     - `LLM_MODEL` = `llama-3.3-70b-versatile`
     - `LLM_TEMPERATURE` = `0.4`
     - `LLM_MAX_TOKENS` = `1024`
     - `DATA_PATH` = `data/processed/zomato_cleaned.csv`
     - `TOP_N_RESULTS` = `5`
     - `MAX_SHORTLIST` = `20`
4. **Set the Start Command**:
   - Go to the **Settings** tab.
   - Under **Deploy** -> **Start Command**, enter:
     ```bash
     python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT
     ```
5. **Generate a Domain**:
   - In the **Settings** tab, under **Networking**, click **Generate Domain**.
   - Copy this new domain (e.g., `zomato-backend-production.up.railway.app`). This is the URL you will put into the frontend `app.js` file.

---

## 3. Deploying the Frontend to Vercel

Vercel is perfect for serving the static files located in the `frontend/` directory.

### Steps:
1. **Push Backend URL**: Make sure you have updated `app.js` with the Railway backend URL from Step 2, committed, and pushed to GitHub.
2. **Create an Account**: Sign up at [Vercel.com](https://vercel.com/) and link your GitHub account.
3. **Add New Project**: Click **Add New** -> **Project** -> Import the `tcl104710-pixel/zomato` repository.
4. **Configure Project**:
   - **Project Name**: Leave as `zomato` or customize it to your preference.
   - **Framework Preset**: Change this to **Other** (Vercel may incorrectly default to Next.js).
   - **Root Directory**: Click "Edit" and select the `frontend` folder. (This tells Vercel to serve the `index.html` from this folder).
   - **Build and Output Settings** (Expand this section to double-check):
     - **Build Command**: Toggle "Override" ON and leave the field **blank**.
     - **Output Directory**: Toggle "Override" ON and leave the field **blank**.
     - **Install Command**: Toggle "Override" ON and leave the field **blank**.
   - **Environment Variables**: No environment variables are needed for the frontend.
5. **Deploy**: Click **Deploy**.
6. **Verify**: Once complete, Vercel will provide a live URL (e.g., `zomato-ai.vercel.app`). Open it to verify the UI loads and successfully communicates with the Railway backend!

---

## 4. Post-Deployment Checklist

- [ ] **CORS Configuration**: By default, `backend/main.py` is configured with `allow_origins=["*"]`. This works for production, but for tighter security, you can update it to only allow your Vercel URL.
- [ ] **Data Availability**: The `zomato_cleaned.csv` is committed in `data/processed/`. Ensure this file is pushed to GitHub so Railway has access to it on startup.
- [ ] **Test E2E**: Perform a search on the Vercel URL and ensure it returns data within ~2-5 seconds.
