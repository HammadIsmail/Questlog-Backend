# Real-Life Dungeon Master — Backend Daemon

A high-performance, asynchronous FastAPI backend powering **Real-Life Dungeon Master** — an automatic productivity telemetry, deterministic scoring, and multi-agent AI accountability system.

---

## Related Repositories

| Repository | Description |
|---|---|
| 🖥️ [Questlog-Desktop-App](https://github.com/HammadIsmail/Questlog-Desktop-App) | WPF Windows desktop client with voice console & telemetry |
| 🧩 [Questlog-Chrome-Extension](https://github.com/HammadIsmail/Questlog-Chrome-Extension) | Manifest V3 browser extension for domain & tab tracking |

---

## Architecture & Features

- **Asynchronous API Engine**: Built on FastAPI, Starlette, and async SQLAlchemy for high-throughput, non-blocking I/O.
- **OpenAI Tool Calling Agent**: Direct function calling for intelligent DB quest management (`create_quest`, `ask_clarification`, `update_quest`, `delete_quest`, `delete_all_quests`, `complete_quest`).
- **Telemetry Batch Ingestion**: High-frequency window activity events ingested concurrently from desktop clients and extensions without locking.
- **Deterministic Scoring Engine**: Concrete productivity metrics evaluated in real time:
  - Base focus points (+10 per 30m productive work, -15 per 30m unproductive)
  - Objective completion rewards (+50 high, +30 medium, +15 low priority)
  - Streak multipliers and category weightings
  - Transparent audit trail logging for every score delta
- **Multi-Agent AI Intelligence**:
  - **Planner Agent**: Generates structured, realistic daily timetable blocks from active quests.
  - **Coach Agent**: Delivers grounded accountability feedback and guidance based on real activity data.
  - **Analytics Agent**: Analyzes weekly trends and computes deep work metrics.
- **AssemblyAI Token Vending**: Mints secure, temporary tokens for real-time speech-to-text WebSocket streaming.
- **Security & Authentication**: JWT bearer tokens, bcrypt password hashing, session validation, and credential management.

---

## Tech Stack

- **Runtime**: Python 3.12+
- **Web Framework**: FastAPI & Uvicorn (ASGI)
- **Tool Calling & LLM**: OpenAI SDK (`openai>=1.55.0`), Groq API (`llama-3.3-70b-versatile`)
- **Speech Intelligence**: AssemblyAI Streaming WebSocket API
- **ORM & DB**: SQLAlchemy 2.0 (Asyncio) + PostgreSQL (`asyncpg`) / Neon Cloud
- **Validation**: Pydantic v2 & `pydantic-settings`
- **Authentication**: `python-jose` (JWT) & `bcrypt`
- **Deployment Platform**: Vercel Serverless (`@vercel/python`)

---

## Project Structure (Vercel Ready)

```text
backend/
├── api/
│   └── index.py             # Vercel serverless entry point (exports 'app')
├── app/
│   ├── main.py              # Application entry point & lifespan
│   ├── config.py            # Settings loaded from environment
│   ├── db/
│   │   ├── session.py       # Async SQLAlchemy engine & session factory
│   │   └── base.py          # Declarative ORM base
│   ├── models/              # Database models (User, Activity, Goal, Schedule, Score)
│   ├── schemas/             # Pydantic validation schemas
│   ├── services/            # Business logic (Scoring, Auth, Activity, Analytics, Tool Agent)
│   ├── agents/              # Multi-agent orchestrators (Planner, Coach, Analytics)
│   └── api/                 # REST endpoints (health, auth, goals, activities, etc.)
├── vercel.json              # Vercel routing & build configuration
├── requirements.txt         # Pinned production dependencies for Vercel
├── .python-version          # Python 3.12 runtime specification
├── pyproject.toml           # Project dependencies & packaging
├── .env.example             # Configuration template
└── README.md
```

---

## Deploying to Vercel

The backend is configured for standard, zero-friction deployment on **Vercel** via serverless Python functions.

### Option A: Deploy via Vercel Dashboard (Recommended)

1. **Push your code to GitHub**:
   Ensure `api/index.py`, `vercel.json`, and `requirements.txt` are committed to your repository.
2. **Import Project in Vercel**:
   - Go to [vercel.com/new](https://vercel.com/new) and connect your GitHub account.
   - Select the repository `Questlog-Backend`.
   - If deploying from a monorepo, set the **Root Directory** to `backend`.
3. **Configure Environment Variables in Vercel Project Settings**:
   Add the following variables under **Project Settings → Environment Variables**:

   | Variable | Description | Example / Recommended Value |
   |---|---|---|
   | `DATABASE_URL` | PostgreSQL connection string (Neon or Supabase) | `postgresql://user:pass@host/db?sslmode=require` |
   | `SECRET_KEY` | 64-char random string for JWT signing | `openssl rand -hex 32` |
   | `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token lifetime | `10080` (7 days) |
   | `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime | `30` |
   | `OPENAI_API_KEY` | OpenAI API key for tool calling | `sk-...` |
   | `GROQ_API_KEY` | Groq API key for fast inference | `gsk_...` |
   | `GROQ_MODEL` | Groq model identifier | `openai/gpt-oss-20b` |
   | `ASSEMBLYAI_API_KEY` | AssemblyAI key for voice streaming | `your_assemblyai_key` |
   | `APP_ENV` | Application environment | `production` |
   | `ALLOWED_ORIGINS` | Permitted CORS origins | `*` |

4. **Deploy**:
   Click **Deploy**. Vercel will build the serverless package and deploy the endpoints.

### Option B: Deploy via Vercel CLI

```bash
# 1. Install Vercel CLI
npm install -g vercel

# 2. Login to Vercel
vercel login

# 3. Deploy to preview
vercel

# 4. Deploy to production
vercel --prod
```

### Verification After Deployment
- **Root Health**: `https://<your-project>.vercel.app/` returns `{"status":"ok","service":"Real-Life Dungeon Master API"}`
- **Interactive Swagger Docs**: `https://<your-project>.vercel.app/docs`
- **Health Check**: `https://<your-project>.vercel.app/api/v1/health`

---

## Local Development

### 1. Prerequisites
- Python 3.12+
- PostgreSQL database (or Neon cloud instance)

### 2. Setup Virtual Environment
```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

### 5. Run Local Server
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health Check: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

---

## Key REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Root verification & API index |
| `GET` | `/api/v1/health` | Service health status |
| `POST` | `/api/v1/auth/register` | Register new adventurer account |
| `POST` | `/api/v1/auth/login` | Authenticate and obtain JWT token |
| `GET` | `/api/v1/auth/me` | Fetch active user profile & validate session |
| `GET` | `/api/v1/goals` | List all active quests |
| `POST` | `/api/v1/goals/from-conversation` | OpenAI Tool Calling voice quest creation/management |
| `POST` | `/api/v1/goals/{id}/complete` | Mark quest complete & award XP points |
| `DELETE`| `/api/v1/goals/{id}` | Delete specific quest |
| `GET` | `/api/v1/voice/token` | Mint short-lived AssemblyAI streaming token |
| `POST` | `/api/v1/activities/batch` | Ingest window telemetry heartbeats |
| `GET` | `/api/v1/analytics/today` | Deep work and productivity analytics |
| `GET` | `/api/v1/score/today` | Current campaign score, streak, and rank |
