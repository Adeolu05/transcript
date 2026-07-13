# Transcript Flow — Deep Technical Audit

**Date:** 2026-07-13  
**Scope:** Full repository (`app/`, `web/`, deploy configs, tests, privacy claims)  
**Status after remediation:** P0 fixes landed in the same change set as this document (see [PR_PLAN.md](./PR_PLAN.md)).

---

## Executive scores (pre-fix → post-fix intent)

| Dimension | Pre | Post (target) | Notes |
|-----------|:---:|:-------------:|-------|
| Architecture / modularity | 8.5 | 8.5 | Shared `extract_guardrails` strengthens consistency |
| Code quality | 8 | 8 | Bucketed rate limits, cleanup loop |
| Security / abuse | 6.5 | **7.5** | Duration estimate, size caps, quota split |
| Reliability / guardrails | 6 | **7.5** | Bot + API same limits; in-process cleanup |
| Production ops | 5.5 | **7** | `data/tmp` + in-process TTL; cron secondary |
| Scalability | 5 | 5.5 | Still in-memory rate limit × workers |
| Testing | 6 | **6.5** | Guardrail + bucket tests added |
| Privacy consistency | 6.5 | **8** | Privacy page + bot copy updated |
| Frontend | 7.5 | 7.5 | Unchanged UX; policy accuracy improved |
| **Overall** | **6.5** | **~7.5** | Soft-launch ready after env review |

---

## Product summary

**Transcript Flow** extracts captions from YouTube/Vimeo and delivers TXT/PDF/DOCX via:

1. FastAPI backend (`app/`)
2. Next.js web (`web/`)
3. Telegram bot (`app/bot/`)

Shared services: transcript fetch, format, file generation, rate limits, analytics/telemetry.

---

## What was already strong

- Modular service layout; bot does not reimplement extraction.
- Structured error envelopes; INTERNAL_ERROR does not leak stack/secrets.
- Path-safe downloads (UUID + extension allowlist; blocks `.raw`).
- Secure XFF handling via `TRUSTED_PROXY_COUNT`.
- Convert reuses `.raw` sidecar; ReportLab uses `html.escape`.
- YouTube proxy/retry/cache path; Docker non-root image.
- Frontend SEO, security headers (Vercel), preview-first UX.

---

## Critical findings (P0) — remediation status

### 1. Render cron could not clean API temp files — **FIXED**

**Problem:** Separate cron container cannot see web service `/tmp`.  
**Fix:**

- Default storage: `<project>/data/tmp` (override `FILE_STORAGE_DIR`).
- Docker/Render set `FILE_STORAGE_DIR=/app/data/tmp`.
- **In-process cleanup loop** in FastAPI lifespan (primary TTL enforcement).
- Cron retained as optional secondary when a shared disk exists.

### 2. Rate limit shared across extract / download / events — **FIXED**

**Problem:** One multi-format session or analytics burned the 10/day extract quota.  
**Fix:** Buckets:

| Bucket | Default | Applied to |
|--------|---------|------------|
| `extract` | 10 / 24h | `POST /extract`, Telegram extract |
| `convert` | 40 / 24h | `POST /convert` |
| `events` | 2000 / 24h | `POST /events` |
| `download` | off | optional via `RATE_LIMIT_DOWNLOAD_ENABLED` |

### 3. Duration `0` bypassed max-duration — **FIXED**

**Problem:** Failed metadata scrape → `duration_seconds=0` → no rejection.  
**Fix:** `extract_guardrails.estimate_duration_seconds` from last caption cue; enforce max duration, max segments, max raw caption chars; formatted text size check.

### 4. Telegram missing VIDEO_TOO_LONG — **FIXED**

**Fix:** Bot calls the same `enforce_transcript_guardrails` as the API.

### 5. Unpinned dependencies — **FIXED**

**Fix:** Version pins in `requirements.txt`.

### 6. Privacy under-disclosed cache/temp — **FIXED**

**Fix:** `web/app/privacy/page.tsx` + Telegram `PRIVACY_TEXT` document temp files and short-term caption cache.

---

## High / medium residual risks (not all fixed)

| ID | Severity | Issue | Recommendation |
|----|----------|--------|----------------|
| R1 | High | In-memory rate limit × Gunicorn workers ≈ N× quota | Redis or `workers=1` for strict caps |
| R2 | High | YouTube/Vimeo HTML scrape fragility | Monitor failures; optional official APIs |
| R3 | Med | SQLite metrics + cache ephemeral without disk | Attach Render disk to `/app/data` |
| R4 | Med | Telegram bot not in `render.yaml` | Deploy as separate worker/service |
| R5 | Med | Full captions on disk in cache (TTL hours) | Accept for MVP; encrypt later if needed |
| R6 | Med | Knowledge-of-UUID download | Accept for anonymous MVP |
| R7 | Low | No bot automated tests | Add handler unit tests with mocks |
| R8 | Low | Health check shallow | Optional deep health for disk write / proxy |

---

## Architecture (current)

```
Web / Telegram
      │
      ▼
 extract_guardrails  ←── shared duration/size policy
      │
 transcript_service → cache → YouTube / Vimeo
      │
 formatter_service → file_service (data/tmp)
      │
 rate_limit (bucketed) · analytics · telemetry
      │
 in-process cleanup (TTL) + optional cron
```

---

## Security checklist

| Area | Status |
|------|--------|
| Path traversal on files | Pass |
| SSRF (arbitrary hosts) | Pass (allowlisted platforms) |
| Error leakage | Pass |
| PDF markup injection | Pass |
| XFF spoofing | Pass if `TRUSTED_PROXY_COUNT` correct |
| Extract abuse | Improved (duration + size + buckets) |
| Multi-worker quota | Residual (R1) |
| Secrets in image | Pass |
| Metrics Basic Auth defaults | Warn on startup if `changeme` |

---

## Test posture

**Present:** formatter, transcript service (mocked), cache, v1 API (mocked), **guardrails**, **rate-limit buckets**.

**Run locally (Windows venv or Linux venv):**

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# Linux: source venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. python -m unittest discover -s tests -v
```

---

## Soft-launch checklist

- [ ] `FRONTEND_URL` + `CORS_EXTRA_ORIGINS` match live origins  
- [ ] `TRUSTED_PROXY_COUNT=1` behind Render/Cloudflare  
- [ ] Strong `METRICS_USERNAME` / `METRICS_PASSWORD`  
- [ ] `NEXT_PUBLIC_API_BASE_URL` set on Vercel production  
- [ ] YouTube proxy env if cloud IP is blocked  
- [ ] Confirm logs show `File storage directory: .../data/tmp`  
- [ ] Confirm cleanup log lines after `CLEANUP_INTERVAL_SECONDS`  
- [ ] Telegram bot: single poller only  

---

## Verdict

Transcript Flow is a serious backend-first utility, not a prototype. After this remediation pass, **controlled public soft launch is reasonable**, provided env vars and YouTube proxy reality are handled. Next scale step: Redis rate limits + persistent disk for `/app/data`.
