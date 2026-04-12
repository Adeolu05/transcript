"""
Protected internal metrics dashboard.
Basic Auth via METRICS_USERNAME / METRICS_PASSWORD from .env.
"""

import html
import secrets
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from app.core.config import settings
from app.services.analytics_service import AnalyticsService

router = APIRouter()


# ---------------------------------------------------------------------------
# Basic Auth helper
# ---------------------------------------------------------------------------

def _check_basic_auth(request: Request) -> bool:
    """Return True if the request carries valid Basic Auth credentials."""
    from base64 import b64decode

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Basic "):
        return False
    try:
        decoded = b64decode(auth[6:]).decode("utf-8")
        username, password = decoded.split(":", 1)
    except Exception:
        return False

    return (
        secrets.compare_digest(username, settings.metrics_username)
        and secrets.compare_digest(password, settings.metrics_password)
    )


# ---------------------------------------------------------------------------
# Dashboard route
# ---------------------------------------------------------------------------

@router.get("/internal/metrics", response_class=HTMLResponse)
async def metrics_dashboard(request: Request):
    if not _check_basic_auth(request):
        return Response(
            content="Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Metrics"'},
        )

    stats_24h = AnalyticsService.get_summary(hours=24)
    stats_7d = AnalyticsService.get_summary(hours=168)

    html = _render_dashboard(stats_24h, stats_7d)
    return HTMLResponse(content=html)


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

def _dist_rows(dist: dict) -> str:
    if not dist:
        return '<tr><td colspan="2" style="color:#888">No data</td></tr>'
    return "".join(
        "<tr><td>"
        f"{html.escape(str(k or '(none)'))}</td><td>{html.escape(str(v))}</td></tr>"
        for k, v in dist.items()
    )


def _render_dashboard(h24: dict, h7d: dict) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TranscriptFlow — Metrics</title>
<style>
  :root {{
    --bg: #0f1117;
    --card: #1a1d27;
    --border: #2a2d37;
    --text: #e4e4e7;
    --muted: #888;
    --accent: #6366f1;
    --green: #22c55e;
    --red: #ef4444;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 2rem;
    line-height: 1.6;
  }}
  h1 {{
    font-size: 1.5rem;
    font-weight: 600;
    margin-bottom: .25rem;
  }}
  .subtitle {{
    color: var(--muted);
    font-size: .85rem;
    margin-bottom: 2rem;
  }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
  }}
  .card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.25rem;
  }}
  .card .label {{
    font-size: .75rem;
    text-transform: uppercase;
    letter-spacing: .05em;
    color: var(--muted);
    margin-bottom: .5rem;
  }}
  .card .value {{
    font-size: 1.75rem;
    font-weight: 700;
  }}
  .card .value.green {{ color: var(--green); }}
  .card .value.red {{ color: var(--red); }}
  .card .value.accent {{ color: var(--accent); }}
  .section-title {{
    font-size: 1rem;
    font-weight: 600;
    margin: 2rem 0 1rem;
    padding-bottom: .5rem;
    border-bottom: 1px solid var(--border);
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 1.5rem;
  }}
  th, td {{
    text-align: left;
    padding: .75rem 1rem;
    border-bottom: 1px solid var(--border);
  }}
  th {{
    font-size: .75rem;
    text-transform: uppercase;
    letter-spacing: .05em;
    color: var(--muted);
    background: rgba(255,255,255,.02);
  }}
  tr:last-child td {{ border-bottom: none; }}
  .two-col {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
  }}
  @media (max-width: 640px) {{
    .two-col {{ grid-template-columns: 1fr; }}
  }}
  .footer {{
    margin-top: 3rem;
    color: var(--muted);
    font-size: .75rem;
    text-align: center;
  }}
</style>
</head>
<body>

<h1>TranscriptFlow Metrics</h1>
<p class="subtitle">Internal operational dashboard</p>

<!-- ── 24h Summary ───────────────────────────────────── -->
<h2 class="section-title">Last 24 Hours</h2>
<div class="grid">
  <div class="card">
    <div class="label">Total Requests</div>
    <div class="value">{h24['total']}</div>
  </div>
  <div class="card">
    <div class="label">Success Rate</div>
    <div class="value green">{h24['success_rate']}%</div>
  </div>
  <div class="card">
    <div class="label">Failures</div>
    <div class="value red">{h24['failures']}</div>
  </div>
  <div class="card">
    <div class="label">Avg Processing</div>
    <div class="value accent">{h24['avg_processing_time_ms']}ms</div>
  </div>
  <div class="card">
    <div class="label">Rate Limit Hits</div>
    <div class="value">{h24['rate_limit_hits']}</div>
  </div>
</div>

<div class="two-col">
  <div>
    <h3 class="section-title">Error Distribution (24h)</h3>
    <table>
      <thead><tr><th>Error Code</th><th>Count</th></tr></thead>
      <tbody>{_dist_rows(h24['error_distribution'])}</tbody>
    </table>
  </div>
  <div>
    <h3 class="section-title">Format Distribution (24h)</h3>
    <table>
      <thead><tr><th>Format</th><th>Count</th></tr></thead>
      <tbody>{_dist_rows(h24['format_distribution'])}</tbody>
    </table>
  </div>
</div>

<div class="two-col">
  <div>
    <h3 class="section-title">Source Distribution (24h)</h3>
    <table>
      <thead><tr><th>Source</th><th>Count</th></tr></thead>
      <tbody>{_dist_rows(h24['source_distribution'])}</tbody>
    </table>
  </div>
  <div></div>
</div>

<!-- ── 7d Summary ────────────────────────────────────── -->
<h2 class="section-title">Last 7 Days</h2>
<div class="grid">
  <div class="card">
    <div class="label">Total Requests</div>
    <div class="value">{h7d['total']}</div>
  </div>
  <div class="card">
    <div class="label">Success Rate</div>
    <div class="value green">{h7d['success_rate']}%</div>
  </div>
  <div class="card">
    <div class="label">Failures</div>
    <div class="value red">{h7d['failures']}</div>
  </div>
  <div class="card">
    <div class="label">Avg Processing</div>
    <div class="value accent">{h7d['avg_processing_time_ms']}ms</div>
  </div>
  <div class="card">
    <div class="label">Rate Limit Hits</div>
    <div class="value">{h7d['rate_limit_hits']}</div>
  </div>
</div>

<div class="two-col">
  <div>
    <h3 class="section-title">Error Distribution (7d)</h3>
    <table>
      <thead><tr><th>Error Code</th><th>Count</th></tr></thead>
      <tbody>{_dist_rows(h7d['error_distribution'])}</tbody>
    </table>
  </div>
  <div>
    <h3 class="section-title">Format Distribution (7d)</h3>
    <table>
      <thead><tr><th>Format</th><th>Count</th></tr></thead>
      <tbody>{_dist_rows(h7d['format_distribution'])}</tbody>
    </table>
  </div>
</div>

<p class="footer">TranscriptFlow v{settings.version} &middot; Internal use only</p>

</body>
</html>"""
