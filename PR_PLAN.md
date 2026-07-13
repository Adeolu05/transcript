# PR Plan — Audit Remediation (2026-07-13)

Stack as independent PRs if you prefer smaller reviews; this change set can also ship as **one** PR titled:

> **fix: production guardrails — cleanup, rate-limit buckets, duration, privacy**

---

## PR1 — File storage + in-process cleanup (P0)

**Goal:** Temp files live where the API can expire them; no reliance on a separate cron filesystem.

| File | Change |
|------|--------|
| `app/core/config.py` | `file_storage_dir`, cleanup interval flags |
| `app/services/file_service.py` | Resolve `data/tmp` (or env); cleanup via logger |
| `app/main.py` | Lifespan cleanup task |
| `app/cleanup.py` | Document secondary/cron role |
| `Dockerfile`, `docker-compose.yml`, `render.yaml` | `FILE_STORAGE_DIR=/app/data/tmp` |
| `.gitignore` | `data/tmp/` |

**Verify:** Start API → extract once → file under `data/tmp` → wait or call `FileGenerator.cleanup_old_files` with short TTL.

---

## PR2 — Rate-limit buckets (P0)

**Goal:** Analytics and downloads do not consume extract quota.

| File | Change |
|------|--------|
| `app/services/rate_limit_service.py` | Bucket keys + per-bucket limits |
| `app/core/dependencies.py` | `verify_rate_limit_extract/convert/events/download` |
| `app/api/v1_routes.py` | Wire dependencies per route |
| `app/bot/telegram_bot.py` | `bucket="extract"` |
| `tests/test_rate_limit_buckets.py` | Independence tests |
| `.env.example`, `render.yaml` | New env vars |

**Verify:** Exhaust extract limit → `/events` still 200; convert still works until convert limit.

---

## PR3 — Shared extract guardrails + bot parity (P0)

**Goal:** One policy for duration/size on web and Telegram.

| File | Change |
|------|--------|
| `app/services/extract_guardrails.py` | **New** estimate + enforce |
| `app/api/v1_routes.py` | Call enforce before/after format |
| `app/bot/telegram_bot.py` | Same enforce; fix `processing_time_ms` |
| `tests/test_extract_guardrails.py` | Duration estimate / reject cases |

**Verify:** Mock transcript with `duration_seconds=0` and last segment at 20_000s → 400 VIDEO_TOO_LONG on API and bot.

---

## PR4 — Dependency pins (P0)

| File | Change |
|------|--------|
| `requirements.txt` | Pinned versions |

**Verify:** Fresh `pip install -r requirements.txt` + unittest suite.

---

## PR5 — Privacy / docs (P0)

| File | Change |
|------|--------|
| `web/app/privacy/page.tsx` | Temp files + cache disclosure |
| `app/bot/telegram_bot.py` | `PRIVACY_TEXT` |
| `README.md` | Accurate claims; Next.js 16 |
| `AUDIT.md`, `PR_PLAN.md` | This audit + plan |
| `DEPLOY_BACKEND.md` / handoff | Env var updates |

---

## PR6 (optional follow-up) — Residual hardening

Not required for soft launch; track separately:

1. Redis (or single worker) for multi-instance rate limits  
2. Render persistent disk for `/app/data`  
3. Telegram worker in `render.yaml` / Compose profile docs only  
4. CI workflow (`unittest` on push)  
5. Bot unit tests  
6. Fail Next production build if `NEXT_PUBLIC_API_BASE_URL` missing  

---

## Suggested merge order

```
PR1 → PR2 → PR3 → PR4 → PR5
```

Or single squash merge if you are the sole owner.

---

## Deploy notes after merge

1. Redeploy API with new env (see `.env.example`).  
2. Redeploy Vercel only if privacy page is production-critical (it is).  
3. Restart Telegram bot process to pick up guardrails + privacy text.  
4. Watch logs for `In-process file cleanup` and extract 429 rates.
