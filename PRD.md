# TRANSCRIPT FLOW

# Execution PRD (Backend-First, SaaS-Ready)

---

# 1️⃣ Product Definition (Locked)

Transcript Flow is a fast, anonymous, infrastructure-grade utility that extracts transcripts from video links and delivers clean downloadable files.

It is the first wedge product of a scalable SaaS company.

Core Value:
Fast → Reliable → Structured → Downloadable.

Not:
AI toy.
Not content marketing gimmick.
Not overloaded SaaS dashboard.

---

# 2️⃣ Product Scope — Phase 1 (Backend MVP)

We are building:

Backend Core Engine
Telegram Interface
Web Interface
Shared API

Backend comes first.

---

# 3️⃣ Backend System Architecture

Your current structure is close. Let’s formalise it.

Recommended refined structure:

```
transcript/
│
├── app/
│   ├── api/                 # FastAPI routes
│   │   ├── v1/
│   │   │   ├── extract.py
│   │   │   ├── health.py
│   │   │   └── download.py
│   │
│   ├── bot/                 # Telegram bot logic
│   │   ├── handlers.py
│   │   ├── keyboards.py
│   │   └── bot.py
│   │
│   ├── services/
│   │   ├── transcript_service.py
│   │   ├── formatting_service.py
│   │   ├── file_service.py
│   │   ├── rate_limit_service.py
│   │   └── metadata_service.py
│   │
│   ├── utils/
│   │   ├── youtube_utils.py
│   │   ├── validators.py
│   │   └── logging_config.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   └── dependencies.py
│   │
│   ├── main.py
│
├── tests/
│
├── web/
│   ├── app/ (Next.js frontend)
│
└── README.md
```

You’re already close. Good sign.

---

# 4️⃣ Backend Responsibilities

The backend is the brain.

It must:

1. Validate URL
2. Extract video ID
3. Fetch transcript
4. Structure transcript
5. Format transcript
6. Generate file
7. Apply rate limiting
8. Return metadata
9. Log analytics

Do not mix these concerns.

Separation is critical.

---

# 5️⃣ Core Service Design

Now let’s define your core services properly.

---

## TranscriptService

Responsibilities:

* Extract video ID
* Fetch transcript via provider
* Return structured transcript object

Output format:

```python
{
  "video_id": str,
  "title": str,
  "language": str,
  "duration": int,
  "segments": [
      {"start": float, "duration": float, "text": str}
  ]
}
```

This structure is non-negotiable.

Future AI features depend on this.

---

## FormattingService

Responsibilities:

* Merge segments
* Remove duplicates
* Clean spacing
* Optional timestamps
* Paragraph optimisation

Must support:

plain
timestamped

Do NOT flatten inside TranscriptService.

---

## FileService

Responsibilities:

* Convert formatted transcript into:

  * TXT
  * PDF
  * DOCX

Must be stateless.

Return file stream or temporary file path.

---

## RateLimitService

Anonymous-first protection:

Web:
IP-based limit

Telegram:
Telegram user ID limit

Basic logic:

* X requests per 24h
* Cooldown logic

Later:
Upgrade to Redis.

For now:
In-memory or lightweight DB.

---

## MetadataService

Tracks:

* Processing time
* Success/failure
* Word count
* Duration
* Language

No transcript storage required.

Metadata only.

This becomes your product intelligence layer.

---

# 6️⃣ API Specification (v1)

---

## POST /api/v1/extract

Request:

```
{
  "url": "https://youtube.com/..."
  "format": "txt" | "pdf" | "docx"
  "include_timestamps": true | false
}
```

Response:

```
{
  "video_title": str,
  "word_count": int,
  "reading_time": int,
  "file_download_url": str
}
```

---

## GET /api/v1/download/{file_id}

Returns file.

Temporary storage:
Delete after X hours.

---

## GET /api/v1/health

Simple status check.

---

# 7️⃣ Telegram Integration

Telegram should NOT bypass backend logic.

Bot must:

* Call internal extract service
* Use same services as API
* Maintain single logic path

Do not duplicate transcript extraction inside bot layer.

Bot is just an interface.

---

# 8️⃣ Web Frontend Integration

Web app calls backend API.

No business logic in frontend.

Frontend responsibilities:

* Input handling
* Loading state
* Display metadata
* Trigger download

Backend does all heavy lifting.

---

# 9️⃣ Phase 1 Feature Scope (Strict)

Do NOT add:

* Accounts
* Playlists
* AI summarisation
* Translation
* History
* Payments

Not yet.

Only:

* YouTube support
* TXT export
* Optional timestamps
* Rate limiting
* Clean error handling

That’s it.

---

# 🔟 Phase 2 Expansion (Pre-Architected)

When Phase 1 is stable:

Add:

* PDF + DOCX
* AI Summary
* Optional login
* Usage dashboard
* Paid tier

Because your backend is modular,
You can plug these in cleanly.

---

# 1️⃣1️⃣ Engineering Principles For This Build

1. No logic duplication.
2. No hard-coded values.
3. Config-driven settings.
4. Logging everywhere.
5. Test transcript_service properly.
6. Clean error messages.

You’re not vibe hacking.
You’re building SaaS infrastructure.

---

# 1️⃣2️⃣ Success Milestone

Before marketing:

Backend stable.
Telegram stable.
Web stable.

Then:

Ship publicly.
Gather feedback.
Track usage.

Then iterate weekly.
