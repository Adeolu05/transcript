# Backend deployment handoff (Transcript Flow)

Give this to whoever deploys the **FastAPI** service (Render, Railway, Fly.io, VPS + Docker, etc.). The **Next.js** site lives on **Vercel** and must point at this API.

## 1. What to send the frontend (Vercel) owner after deploy

As soon as the API has a **public HTTPS URL** (no trailing slash), send:

| Name | Example value | Notes |
|------|----------------|-------|
| `NEXT_PUBLIC_API_BASE_URL` | `https://transcriptflow-api.onrender.com` | **Exact** URL Vercel Production will use. |

They add it in **Vercel → Project → Settings → Environment Variables → Production**.

---

## 2. Required environment variables (API)

Values below match `app/core/config.py`. Names are the usual `UPPER_SNAKE` env names Pydantic reads.

### Must set for production

| Variable | Example | Purpose |
|----------|---------|---------|
| `DEBUG` | `false` | Disables dev behaviour; enables startup warning if metrics password is default. |
| `FRONTEND_URL` | `https://www.usetranscriptflow.com` | **Primary** browser origin for CORS (your canonical marketing URL). |
| `CORS_EXTRA_ORIGINS` | `https://usetranscriptflow.com` | Optional comma-separated **extra** origins (apex if you redirect to www, Vercel preview URLs if previews should call **this** API). |
| `TRUSTED_PROXY_COUNT` | `1` | **1** when the app sits behind one reverse proxy (Render/Railway/Nginx/Cloudflare). Use `0` only for raw local/dev. |
| `METRICS_USERNAME` | (strong unique) | Basic Auth user for `/internal/metrics`. |
| `METRICS_PASSWORD` | (strong unique) | **Not** `changeme` in production. |

### Strongly recommended

| Variable | Notes |
|----------|--------|
| `TELEGRAM_BOT_TOKEN` | If you run the Telegram worker (`docker compose --profile bot` or separate process). |
| `SENTRY_DSN` | Error monitoring for the API. |

### Defaults usually OK (tune if needed)

| Variable | Default | Purpose |
|----------|---------|---------|
| `RATE_LIMIT_REQUESTS` | `10` | Per-IP **extract** requests per window. |
| `RATE_LIMIT_WINDOW_SECONDS` | `86400` | Window (24h). |
| `RATE_LIMIT_CONVERT_REQUESTS` | `40` | Per-IP convert (PDF/DOCX) quota. |
| `RATE_LIMIT_EVENTS_REQUESTS` | `2000` | Per-IP telemetry quota (0 = unlimited). |
| `RATE_LIMIT_DOWNLOAD_ENABLED` | `false` | When true, downloads use a separate bucket. |
| `MAX_VIDEO_DURATION_SECONDS` | `10800` | Max video length (3h); estimated from captions if metadata missing. |
| `MAX_TRANSCRIPT_SEGMENTS` | `20000` | Hard cap on caption cue count. |
| `TRANSCRIPT_TIMEOUT_SECONDS` | `15` | Upstream transcript timeout. |
| `FILE_STORAGE_DIR` | `/app/data/tmp` (Docker) | Generated file directory. |
| `FILE_TTL_HOURS` | `1` | Temp files + cleanup age. |
| `IN_PROCESS_CLEANUP_ENABLED` | `true` | API lifespan TTL cleaner (primary on PaaS). |
| `CLEANUP_INTERVAL_SECONDS` | `900` | How often in-process cleanup runs. |
| `CONVERT_MAX_CONCURRENCY` | `2` | Parallel PDF/DOCX conversions. |
| `TRANSCRIPT_CACHE_ENABLED` | `true` | Disk cache for repeat URLs. |
| `TRANSCRIPT_CACHE_TTL_HOURS` | `72` | Cache freshness. |

### Required on cloud hosts (YouTube IP blocks)

YouTube blocks most datacenter IPs. The Telegram bot and `/extract` then fail for **every** link, including English videos. The old user text talked about English-only captions. That was an IP block.

Set a **residential** proxy on the API **and** the bot process (same env):

| Variable | Purpose |
|----------|---------|
| `WEBSHARE_PROXY_USERNAME` | Webshare rotating residential user |
| `WEBSHARE_PROXY_PASSWORD` | Webshare password |
| `WEBSHARE_PROXY_LOCATIONS` | Optional country codes, e.g. `us,de` |

Or generic HTTP(S) proxies: `YOUTUBE_HTTP_PROXY_URL`, `YOUTUBE_HTTPS_PROXY_URL`.

Without one of these, cloud Telegram will keep failing. Local home IPs often work with no proxy.

---

## 3. CORS checklist (avoid “failed to fetch” on the live site)

- **`FRONTEND_URL`** must equal the **exact** origin users use in the browser, including `https` and **no** trailing slash, e.g. `https://www.usetranscriptflow.com`.
- If both **apex** and **www** can load the app, set e.g.  
  `CORS_EXTRA_ORIGINS=https://usetranscriptflow.com`  
  (comma-separated, no spaces).
- After changing env vars, **redeploy** the API so the new CORS list loads.

---

## 4. Health check & routing

- **Health URL:** `GET /api/v1/health` (used by Render `healthCheckPath` in `render.yaml`).
- **Metrics (internal):** `GET /internal/metrics` — protect with strong Basic Auth; do not expose without auth.

---

## 5. Render (reference)

`render.yaml` in the repo defines:

- **Web service:** Docker image, health check `/api/v1/health`.
- **Cron:** `python -m app.cleanup` every 15 minutes (temp file cleanup).

Sync **secret** env vars in the Render dashboard (`TELEGRAM_BOT_TOKEN`, `SENTRY_DSN`, `METRICS_*`). Set `FRONTEND_URL` / `CORS_EXTRA_ORIGINS` to match production **www** + apex as needed.

---

## 6. Railway / Fly / raw Docker

- Run the same env vars as above.
- **HTTPS** must terminate in front of the app (platform TLS or reverse proxy).
- Set **`TRUSTED_PROXY_COUNT=1`** when the platform injects `X-Forwarded-For`.
- Schedule **`python -m app.cleanup`** on a timer (like Render cron) so temp files do not fill disk.

---

## 7. Vercel: Production vs Preview (for the frontend owner)

### Production

1. Vercel → **Settings → Environment Variables**.
2. Add **`NEXT_PUBLIC_API_BASE_URL`** = your **production** API URL, e.g. `https://your-api.onrender.com` (HTTPS, **no** trailing slash).
3. Scope: **Production** only (or also Preview if you choose option B below).
4. **Redeploy** the site so the variable is baked into the client bundle.

### Preview deployments (choose one)

**A — Previews use production API (simplest)**  
- Do **not** set `NEXT_PUBLIC_API_BASE_URL` for Preview (or set it to the **same** production API URL).  
- **Risk:** preview URLs share production **rate limits** and traffic; fine for internal QA, not ideal for public preview links.

**B — Previews use a staging API (cleanest)**  
- Deploy a **second** API (staging) with its own URL.  
- In Vercel, set **`NEXT_PUBLIC_API_BASE_URL`** for **Preview** to the staging URL.  
- On staging API, set **`FRONTEND_URL`** (and **`CORS_EXTRA_ORIGINS`**) to include every Vercel preview origin you use, e.g.  
  `https://your-project-*.vercel.app` is **not** supported as a wildcard in CORS — you must list concrete preview URLs or use a **stable** preview domain / branch domain Vercel gives you. Practically: add each preview base URL you care about, or accept option A.

**C — Previews do not call the API**  
- Only test UI; transcribe will fail until merged to production — rarely worth it.

**Note:** Middleware redirects **production** `*.vercel.app` traffic to **`https://www.usetranscriptflow.com`**. Preview deployments keep the `*.vercel.app` host unless you add more rules.

---

## 8. Handoff checklist

- [ ] API reachable over **HTTPS**.
- [ ] `GET /api/v1/health` returns 200.
- [ ] `FRONTEND_URL` + optional `CORS_EXTRA_ORIGINS` match real browser origins.
- [ ] `TRUSTED_PROXY_COUNT` matches hosting (usually `1`).
- [ ] `METRICS_PASSWORD` changed from default.
- [ ] Cron or equivalent runs `python -m app.cleanup`.
- [ ] Production **`NEXT_PUBLIC_API_BASE_URL`** sent to Vercel and redeployed.

---

## 9. Contact between teams

**Backend → Frontend:** public API base URL (HTTPS, no trailing slash).  
**Frontend → Backend:** canonical site URL(s) for CORS (`www` + apex if both used).
