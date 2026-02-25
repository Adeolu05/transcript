from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "TranscriptFlow API"
    version: str = "1.0.0"
    debug: bool = False
    telegram_bot_token: str = "YOUR_TOKEN_HERE"
    frontend_url: str = "http://localhost:3000"

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

    class Config:
        env_file = ".env"

settings = Settings()
