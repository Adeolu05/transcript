from __future__ import annotations

import random
import time
import requests
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    CouldNotRetrieveTranscript,
    Transcript,
    TranscriptList,
    TranscriptsDisabled,
    VideoUnavailable,
    NoTranscriptFound,
    NotTranslatable,
    TranslationLanguageNotAvailable,
    IpBlocked,
    RequestBlocked,
)

from app.utils.validators import detect_platform, validate_youtube_url, validate_vimeo_url
from app.services.vimeo_service import get_vimeo_transcript
from app.services.transcript_cache_service import (
    read_transcript_cache,
    write_transcript_cache,
)
from app.core.config import settings
from app.core.errors import ErrorCode, TranscriptFetchError

# User-facing when YouTube IpBlocked / RequestBlocked (cloud IPs are often banned).
YOUTUBE_TRANSCRIPT_UNAVAILABLE_EN_ONLY = (
    "We could not load captions because YouTube blocked this server. "
    "Please try again later."
)

YOUTUBE_TIMEOUT_MESSAGE = "Transcript provider did not respond in time."

_OEMBED_URL = "https://www.youtube.com/oembed"
# Title only names the download; never hold captions back for long waiting on it.
_METADATA_GRACE_SECONDS = 1.5
_metadata_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="yt-metadata")


class _DeadlineExceeded(Exception):
    """The caller's time budget ran out before the next upstream request."""


class _DeadlineSession(requests.Session):
    """
    Caps each request at the time left before *deadline* (time.monotonic()).
    asyncio.wait_for cannot stop the worker thread, so this is what makes a
    timed-out extract stop calling YouTube (and spending proxy bandwidth).
    """

    def __init__(self, deadline: float):
        super().__init__()
        self._deadline = deadline

    def request(self, *args, **kwargs):
        remaining = self._deadline - time.monotonic()
        if remaining <= 0:
            raise _DeadlineExceeded()
        timeout = kwargs.get("timeout")
        kwargs["timeout"] = min(timeout, remaining) if isinstance(timeout, (int, float)) else remaining
        return super().request(*args, **kwargs)


# Fallback search order after the client’s target language (never English-only).
_BASE_LANG_PRIORITY: Tuple[str, ...] = (
    "en",
    "en-US",
    "en-GB",
    "en-IN",
    "en-IE",
    "es",
    "es-419",
    "es-ES",
    "pt",
    "pt-PT",
    "pt-BR",
    "fr",
    "fr-FR",
    "de",
    "it",
    "ja",
    "ko",
    "zh-Hans",
    "zh-Hant",
    "zh-TW",
    "hi",
    "ar",
    "ru",
    "nl",
    "pl",
    "tr",
    "vi",
    "id",
    "th",
    "uk",
    "sv",
    "no",
    "da",
    "fi",
    "el",
    "he",
    "cs",
    "ro",
    "hu",
    "ms",
    "bn",
    "ta",
    "te",
    "mr",
)


def _youtube_proxy_configured() -> bool:
    return bool(
        (settings.webshare_proxy_username and settings.webshare_proxy_password)
        or (settings.youtube_http_proxy_url or settings.youtube_https_proxy_url)
    )


def _youtube_ip_block_attempts() -> int:
    n = max(1, int(settings.youtube_transcript_retry_max))
    if not _youtube_proxy_configured():
        return 1
    return min(n, 8)


def _youtube_api(deadline: Optional[float] = None) -> YouTubeTranscriptApi:
    """
    Optional residential / generic proxies — see youtube-transcript-api README
    https://github.com/jdepoix/youtube-transcript-api#working-around-ip-bans
    """
    http_client = _DeadlineSession(deadline) if deadline is not None else None
    proxy_config = None
    try:
        from youtube_transcript_api.proxies import GenericProxyConfig, WebshareProxyConfig
    except ImportError:
        WebshareProxyConfig = None  # type: ignore[misc, assignment]
        GenericProxyConfig = None  # type: ignore[misc, assignment]

    if (
        WebshareProxyConfig
        and settings.webshare_proxy_username
        and settings.webshare_proxy_password
    ):
        loc_raw = (settings.webshare_proxy_locations or "").strip()
        locations = [x.strip().lower() for x in loc_raw.split(",") if x.strip()] or None
        proxy_config = WebshareProxyConfig(
            proxy_username=settings.webshare_proxy_username,
            proxy_password=settings.webshare_proxy_password,
            filter_ip_locations=locations,
        )
    elif GenericProxyConfig and (
        settings.youtube_http_proxy_url or settings.youtube_https_proxy_url
    ):
        proxy_config = GenericProxyConfig(
            http_url=settings.youtube_http_proxy_url or None,
            https_url=settings.youtube_https_proxy_url or None,
        )

    return YouTubeTranscriptApi(proxy_config=proxy_config, http_client=http_client)


def get_transcript_from_url(url: str, deadline: Optional[float] = None) -> Dict:
    """
    Fetch transcript. YouTube captions are always resolved to English (native or auto-translate).
    Raises TranscriptFetchError for expected failures; anything else is a bug.
    *deadline* (time.monotonic()) bounds upstream work so it stops once the caller gives up.
    """
    try:
        platform = detect_platform(url)
        video_id = (
            validate_youtube_url(url) if platform == "youtube" else validate_vimeo_url(url)
        )
    except ValueError as e:
        raise TranscriptFetchError(ErrorCode.INVALID_URL, str(e)) from e

    cached = read_transcript_cache(platform, video_id)
    if cached is not None:
        out = dict(cached)
        if url:
            out["source_url"] = url
        return out

    if platform == "youtube":
        result = get_youtube_transcript(video_id, url=url, deadline=deadline)
    else:
        result = get_vimeo_transcript(video_id, url=url, deadline=deadline)
    write_transcript_cache(platform, video_id, result)
    return result


def _get_youtube_metadata(video_id: str) -> Dict:
    """
    Title via oEmbed: a small JSON endpoint that is rarely blocked, unlike the
    watch page. Duration isn't exposed there; extract_guardrails estimates it
    from the last caption cue when this is 0.
    """
    fallback = {"title": f"YouTube Video {video_id}", "duration": 0}
    try:
        response = requests.get(
            _OEMBED_URL,
            params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
            timeout=5,
        )
        response.raise_for_status()
        title = str(response.json().get("title") or "").strip()
        return {"title": title or fallback["title"], "duration": 0}
    except (requests.RequestException, ValueError):
        return fallback


def _resolve_metadata(future: Future, video_id: str) -> Dict:
    try:
        return future.result(timeout=_METADATA_GRACE_SECONDS)
    except Exception:
        return {"title": f"YouTube Video {video_id}", "duration": 0}


def _language_priority_tuple() -> Tuple[str, ...]:
    raw = (settings.youtube_transcript_language_priority or "").strip()
    user = [p.strip() for p in raw.split(",") if p.strip()] if raw else []
    merged = list(dict.fromkeys(user + list(_BASE_LANG_PRIORITY)))
    return tuple(merged)


def _norm_lang_base(code: str) -> str:
    return (code or "").strip().split("-")[0].lower()


def _select_transcript_for_priority(
    tlist: TranscriptList, priority: Tuple[str, ...]
) -> Transcript:
    cleaned = tuple(dict.fromkeys(p for p in priority if p))
    try:
        return tlist.find_transcript(cleaned)
    except NoTranscriptFound:
        for tr in tlist:
            return tr
        raise NoTranscriptFound(tlist.video_id, list(cleaned), tlist) from None


def _translation_api_code_for_target(tr: Transcript, target_base: str) -> Optional[str]:
    """Exact language_code to pass to translate(), matching YouTube’s list."""
    if not tr.is_translatable or not target_base:
        return None
    for tl in tr.translation_languages:
        if _norm_lang_base(tl.language_code) == target_base:
            return tl.language_code
    return None


def _fetch_for_target_language(tr: Transcript, target_language: str) -> Tuple[Any, str]:
    """
    Return (fetched_transcript, language_code). Prefer native track in *target_language*,
    else YouTube translate(), else original captions.
    """
    tgt = _norm_lang_base(target_language)
    src = _norm_lang_base(tr.language_code)
    if tgt and src == tgt:
        fetched = tr.fetch()
        return fetched, fetched.language_code

    api_code = _translation_api_code_for_target(tr, tgt) if tgt else None
    if api_code:
        try:
            fetched = tr.translate(api_code).fetch()
            return fetched, fetched.language_code
        except (TranslationLanguageNotAvailable, NotTranslatable, Exception):
            pass

    if tgt:
        try:
            fetched = tr.translate(target_language).fetch()
            return fetched, fetched.language_code
        except (TranslationLanguageNotAvailable, NotTranslatable):
            pass

    fetched = tr.fetch()
    return fetched, fetched.language_code


def _youtube_transcript_fresh_core(
    video_id: str,
    languages: Optional[List[str]],
    url: str,
    metadata_future: Optional[Future] = None,
    deadline: Optional[float] = None,
) -> Dict:
    if metadata_future is None:
        metadata_future = _metadata_pool.submit(_get_youtube_metadata, video_id)
    api = _youtube_api(deadline)
    tlist = api.list(video_id)

    target = "en"

    if languages is not None:
        transcript = tlist.find_transcript(tuple(languages))
        fetched = transcript.fetch()
        out_lang = fetched.language_code
    else:
        priority = tuple(
            dict.fromkeys(
                [target, _norm_lang_base(target), *list(_language_priority_tuple())]
            )
        )
        priority = tuple(p for p in priority if p)
        transcript = _select_transcript_for_priority(tlist, priority)
        fetched, out_lang = _fetch_for_target_language(transcript, target)

    segments = [
        {"text": item.text, "start": item.start, "duration": item.duration}
        for item in fetched
    ]
    metadata = _resolve_metadata(metadata_future, video_id)

    return {
        "provider": "youtube",
        "source_url": url,
        "video_id": video_id,
        "title": metadata["title"],
        "language": out_lang,
        "duration_seconds": metadata["duration"],
        "segments": segments,
    }


def _youtube_fetch_error(e: CouldNotRetrieveTranscript) -> TranscriptFetchError:
    """Map youtube-transcript-api failures to a user-safe TranscriptFetchError."""
    na = ErrorCode.TRANSCRIPT_NOT_AVAILABLE
    if isinstance(e, (IpBlocked, RequestBlocked)):
        return TranscriptFetchError(
            ErrorCode.UPSTREAM_BLOCKED, YOUTUBE_TRANSCRIPT_UNAVAILABLE_EN_ONLY
        )
    if isinstance(e, TranscriptsDisabled):
        return TranscriptFetchError(na, "Transcripts are disabled for this video.")
    if isinstance(e, VideoUnavailable):
        return TranscriptFetchError(na, "Video is unavailable.")
    if isinstance(e, NoTranscriptFound):
        return TranscriptFetchError(
            na,
            "No transcript or captions are available for this video in any language we could access.",
        )
    return TranscriptFetchError(na, "Captions could not be retrieved for this video.")


def get_youtube_transcript(
    video_id: str,
    languages: Optional[List[str]] = None,
    url: str = "",
    deadline: Optional[float] = None,
) -> Dict:
    """
    list() + find_transcript; never uses fetch(video_id) default ['en'] shortcut.
    English-only: prefer English captions, else translate to English when available.
    With residential proxy configured, retries a few times on IpBlocked / RequestBlocked,
    but never sleeps past *deadline*.
    """
    # Title fetch runs alongside the caption requests (and survives retries)
    metadata_future = _metadata_pool.submit(_get_youtube_metadata, video_id)
    attempts = 1 if languages is not None else _youtube_ip_block_attempts()
    for attempt in range(attempts):
        try:
            return _youtube_transcript_fresh_core(
                video_id, languages, url, metadata_future=metadata_future, deadline=deadline
            )
        except (IpBlocked, RequestBlocked) as e:
            delay = settings.youtube_transcript_retry_backoff_seconds * (attempt + 1)
            delay += random.uniform(0, 0.25)
            out_of_time = deadline is not None and time.monotonic() + delay >= deadline
            if attempt < attempts - 1 and not out_of_time:
                time.sleep(delay)
                continue
            raise _youtube_fetch_error(e) from e
        except CouldNotRetrieveTranscript as e:
            raise _youtube_fetch_error(e) from e
        except (_DeadlineExceeded, requests.Timeout) as e:
            raise TranscriptFetchError(ErrorCode.UPSTREAM_TIMEOUT, YOUTUBE_TIMEOUT_MESSAGE) from e
        except requests.RequestException as e:
            raise TranscriptFetchError(
                ErrorCode.TRANSCRIPT_NOT_AVAILABLE, "Could not reach YouTube. Try again later."
            ) from e
    raise AssertionError("unreachable")


def get_transcript(video_id: str, languages: Optional[List[str]] = None) -> Optional[Dict]:
    if languages is None:
        return get_youtube_transcript(video_id, url="")
    return get_youtube_transcript(video_id, languages=languages, url="")
