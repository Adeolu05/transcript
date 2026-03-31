# Transcript Flow

Transcript Flow is a fast, anonymous, infrastructure-grade utility that extracts transcripts from video links and delivers clean downloadable files. It is designed as a high-performance backend-first system with interfaces for both the Web and Telegram.

Core Value: **Fast → Reliable → Structured → Downloadable.**

![Transcript Flow App](web/public/brand/telegram-avatar-1024.png)

## 🌟 Key Features

- **Multi-Platform Support**: Extract transcripts from **YouTube** and **Vimeo** instantly.
- **Clean Formats**: Download as **TXT, PDF, and DOCX**.
- **Timestamps**: Toggle perfectly formatted timestamps on or off.
- **Anonymous & Secure**: No accounts required. No persistent storage. Files auto-delete after 1 hour (TTL).
- **Rate Limited & Guardrailed**: IP and User ID-based limits, along with max video duration and timeout protections.
- **Telemetry & Analytics**: Built-in lightweight JSON-structured logging and analytics tracking.

## 🏗 System Architecture

Transcript Flow is built with a strict separation of concerns, heavily prioritizing backend modularity for future AI expansion.

- **Backend Logic (Brain)**: Python & FastAPI
- **Web Interface**: Next.js & React (TailwindCSS)
- **Telegram Interface**: `python-telegram-bot` 

### Directory Structure

```text
transcript/
├── app/                      # Python Backend (FastAPI + Telegram Bot)
│   ├── api/                  # FastAPI routing (v1 endpoints, metrics)
│   ├── bot/                  # Telegram bot logic (handlers, components)
│   ├── services/             # Core business logic (Extract, Format, File, Rate Limit)
│   ├── core/                 # Config, Errors, Dependencies
│   ├── utils/                # Logging, Regex Validators
│   └── main.py               # FastAPI entry point
├── web/                      # Next.js Frontend (React, Tailwind)
│   ├── app/                  # App Router pages (/, /app)
│   ├── components/           # React Components (Hero, UI elements)
│   └── public/               # Static assets & branding
├── tests/                    # Unit testing suite
├── Dockerfile                # Render deployment configuration for Backend
└── requirements.txt          # Python dependencies
```

## 🚀 Interfaces

### 1. Web Application (`/web`)
A premium, modern SaaS web app interface designed with:
- 3D Video Carousel hero section.
- Preview-First Results Flow: Shows a snippet of the transcript immediately, followed by format selection (TXT/PDF/DOCX).
- Clean state-machine interactions (Idle → Processing → Success/Error).

### 2. Telegram Bot (`app/bot/telegram_bot.py`)
A seriously structured, minimal utility bot:
- **Instant Processing**: Send a URL, get a file. No conversational fluff.
- **In-Memory Preferences**: Remembers your preferred format (e.g., PDF) and timestamp preferences across sessions.
- **Single Message UX**: Status updates (Extracting... $\rightarrow$ Formatting... $\rightarrow$ Ready) happen within a single edited message to keep chat history clean.
- **Branded Onboarding**: Clean `/start` experience with inline keyboard routing.

### 3. Shared API (`app/api`)
Both the Web App and Telegram Bot route through the identical core service modules (`TranscriptService`, `FileService`, etc.) guaranteeing total consistency.

## 🛠 Tech Stack

- **Backend**: Python 3.12, FastAPI, Uvicorn, Gunicorn
- **Frontend**: Next.js 14, React, Tailwind CSS, Framer Motion
- **Transcripts**: `youtube-transcript-api`
- **Generators**: `reportlab` (PDF), `python-docx` (Word)
- **Deployment**: Docker, designed for Render/Railway scaling.

## ⚙️ Local Development

### Prerequisites
- Python 3.12+
- Node.js 18+

### 1. Backend Setup

```bash
# Clone the repository and setup virtual environment
python -m venv venv
source venv/bin/activate  # OR venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Create environment configuration
cp .env.example .env
# Edit .env and supply your TELEGRAM_BOT_TOKEN and other overrides
```

Run the FastAPI Server:
```bash
uvicorn app.main:app --reload --port 8000
```

Run the Telegram Bot:
```bash
python -m app.bot.telegram_bot
```

### 2. Frontend Setup

```bash
cd web

# Install dependencies
npm install

# Run the Next.js dev server
npm run dev
```
The web app will be available at `http://localhost:3000`.

## 🔒 Production Readiness

The Phase 1 MVP comes with production-grade guardrails:
- **Error Envelopes**: Unified structured JSON error responses.
- **Timeout Protection**: `asyncio.wait_for()` applied to upstream transcript providers.
- **Threadpool Offloading**: CPU-bound tasks (PDF/DOCX generation) use asynchronous threading logic so the event loop never blocks.
- **Strict Headers**: Fully configurable proxy depth and CORS security.
- **Sentry Integration**: Exception tracking supported via `SENTRY_DSN`.

---

© 2026 Transcript Flow. All rights reserved.