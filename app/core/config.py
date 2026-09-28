from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )
    app_name: str = "TranscriptFlow API"
    version: str = "1.0.0"
    debug: bool = False
    telegram_bot_token: str = "YOUR_TOKEN_HERE"
    frontend_url: str = "http://localhost:3000"
    # Comma-separated extra browser origins allowed by CORS (same creds as FRONTEND_URL).
    # Use for apex + www, or extra deploy URLs without changing the primary FRONTEND_URL.
    cors_extra_origins: str = ""

    # Rate limiting — extract is the scarce resource; download/events use separate/no quota
    rate_limit_requests: int = 10
    rate_limit_window_seconds: int = 86400  # 24 hours
    # PDF/DOCX conversion (separate bucket so one extract can convert multiple formats)
    rate_limit_convert_requests: int = 40
    # Product telemetry (high ceiling; 0 = unlimited)
    rate_limit_events_requests: int = 2000
    # When True, GET /download counts against a light shared bucket; default off
    rate_limit_download_enabled: bool = False
    rate_limit_download_requests: int = 200
    # AI summaries: counted only when Claude is actually called (cache hits are free)
    rate_limit_summarize_requests: int = 3

    # AI summaries (Claude). Empty key = feature hidden and endpoint disabled.
    anthropic_api_key: str = ""
    summary_model: str = "claude-opus-5-5"
    # Summaries are a simple task; low effort keeps thinking (and cost) small
    summary_effort: str = "low"
    # ~50K tokens; longer transcripts are refused rather than silently truncated
    summary_max_input_chars: int = 200_000
    summary_timeout_seconds: float = 90.0

    # Optional shared store (e.g. redis://...). When set, rate limits are counted
    # across all Gunicorn workers + the Telegram bot, and bot preferences survive
    # restarts. Empty or unreachable = per-process in-memory fallback.
    redis_url: str = ""
    telegram_prefs_ttl_days: int = 90

    # Key for HMAC-hashing IPs / Telegram IDs in logs and telemetry. Unset = a
    # random per-process key (hashes then only correlate within one process).
    log_hash_secret: str = ""

    # Proxy security: how many trusted proxies sit in front of the app.
    # 0 = direct exposure (ignore X-Forwarded-For entirely, use socket IP).
    # 1 = one reverse proxy (Nginx, Cloudflare, etc.).
    trusted_proxy_count: int = 0

    # Safety guardrails
    max_video_duration_seconds: int = 10800  # 3 hours
    transcript_timeout_seconds: int = 15
    max_raw_text_length: int = 500_000  # ~500 KB, prevents huge PDF builds
    max_transcript_segments: int = 20_000
    convert_max_concurrency: int = 2  # max parallel PDF/DOCX conversions

    # File storage + TTL
    # Empty = <project>/data/tmp (Docker Compose mounts /app/data so cleanup & API share files)
    file_storage_dir: str = ""
    file_ttl_hours: int = 1  # cleanup age + surfaced to frontend
    # In-process cleanup (primary on multi-service PaaS where cron cannot see API /tmp)
    in_process_cleanup_enabled: bool = True
    cleanup_interval_seconds: int = 900  # 15 minutes

    # TTF used for PDFs whose text is beyond Helvetica's Western European set
    # (Polish, Vietnamese, Cyrillic, Greek...). Empty = search common system paths.
    pdf_font_path: str = ""

    # Telegram bot preview length
    preview_chars: int = 1500

    # Internal metrics dashboard
    metrics_username: str = "admin"
    metrics_password: str = "changeme"

    # Sentry (empty DSN = disabled)
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1

    # Optional comma-separated codes to try *before* the built-in list in transcript_service
    youtube_transcript_language_priority: str = ""

    # YouTube transcript API — optional proxies (cloud IPs are often blocked; see library README)
    webshare_proxy_username: str = ""
    webshare_proxy_password: str = ""
    # Optional comma-separated ISO country codes for Webshare IP pool, e.g. "de,us"
    webshare_proxy_locations: str = ""
    youtube_http_proxy_url: str = ""
    youtube_https_proxy_url: str = ""

    # Transcript cache (disk) — repeat requests skip YouTube/Vimeo when fresh
    transcript_cache_enabled: bool = True
    transcript_cache_ttl_hours: int = 72
    # Empty = project data/transcript_cache/
    transcript_cache_dir: str = ""

    # YouTube: extra attempts on IpBlocked/RequestBlocked (useful with rotating residential proxy)
    youtube_transcript_retry_max: int = 3
    youtube_transcript_retry_backoff_seconds: float = 0.65

    def resolved_file_storage_dir(self) -> Path:
        raw = (self.file_storage_dir or "").strip()
        if raw:
            return Path(raw)
        return _project_root() / "data" / "tmp"


settings = Settings()
