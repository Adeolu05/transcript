from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Rate limiting
    rate_limit_requests: int = 10
    rate_limit_window_seconds: int = 86400  # 24 hours

    # Proxy security: how many trusted proxies sit in front of the app.
    # 0 = direct exposure (ignore X-Forwarded-For entirely, use socket IP).
    # 1 = one reverse proxy (Nginx, Cloudflare, etc.).
    trusted_proxy_count: int = 0

    # Safety guardrails
    max_video_duration_seconds: int = 10800  # 3 hours
    transcript_timeout_seconds: int = 15
    max_raw_text_length: int = 500_000  # ~500 KB, prevents huge PDF builds
    convert_max_concurrency: int = 2    # max parallel PDF/DOCX conversions

    # File TTL
    file_ttl_hours: int = 1  # cleanup age + surfaced to frontend

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


settings = Settings()
