/**
 * FastAPI base URL (no trailing slash).
 * When NEXT_PUBLIC_API_BASE_URL is unset, local dev uses 127.0.0.1:8000 so the
 * transcribe page works without web/.env.local. Production builds must set the env var.
 */
const raw = (process.env.NEXT_PUBLIC_API_BASE_URL ?? '').trim();

export const PUBLIC_API_BASE = raw
  ? raw.replace(/\/$/, '')
  : 'http://127.0.0.1:8000';
