# Real-Life Dungeon Master — Backend Daemon

A high-performance, asynchronous FastAPI backend that powers **Real-Life Dungeon Master** — an automatic productivity telemetry, scoring, and multi-agent AI accountability system.

---

## Related Repositories

| Repository | Description |
|---|---|
| 🖥️ [Questlog-Desktop-App](https://github.com/HammadIsmail/Questlog-Desktop-App) | WPF Windows desktop client with Win32 telemetry |
| 🧩 [Questlog-Chrome-Extension](https://github.com/HammadIsmail/Questlog-Chrome-Extension) | Manifest V3 browser extension for domain tracking |

---

## Architecture & Features

- **Asynchronous API Engine**: Built on FastAPI, Starlette, and async SQLAlchemy for non-blocking I/O.
- **Telemetry Batch Ingestion**: Ingests high-frequency window activity events from desktop clients and browser extensions without locking.
- **Deterministic Scoring Engine**: Real-time evaluation of user actions based on concrete rules:
  - Base focus points (+10 per 30m productive work, -15 per 30m unproductive)
  - Objective completion rewards (+50 high, +30 medium, +15 low priority)
  - Streak multipliers and category weightings
  - Transparent audit trail logging for every score delta
- **Multi-Agent AI Intelligence**:
  - **Planner Agent**: Generates structured, realistic daily timetable blocks from active quests.
  - **Coach Agent**: Delivers grounded, no-nonsense accountability feedback and guidance based on real activity data.
  - **Analytics Agent**: Analyzes weekly trends and computes deep work metrics.
- **Security & Authentication**: JWT bearer tokens, bcrypt password hashing, and user credential management.

---

## Tech Stack

- **Runtime**: Python 3.12+
- **Web Framework**: FastAPI & Uvicorn
- **ORM**: SQLAlchemy 2.0 (Asyncio)
- **Database**: PostgreSQL (via `asyncpg`) / SQLite fallback for local testing
- **Validation**: Pydantic v2 & `pydantic-settings`
- **Authentication**: `python-jose` (JWT) & `passlib` (Bcrypt)

---

## Directory Structure

```
backend/
├── app/
│   ├── main.py              # Application entry point & lifespan
│   ├── config.py            # Settings loaded from environment
│   ├── db/
│   │   ├── session.py       # Async SQLAlchemy engine & session factory
│   │   └── base.py          # Declarative ORM base
│   ├── models/              # Database models (User, Activity, Goal, Schedule, Score)
│   ├── schemas/             # Pydantic validation schemas
│   ├── services/            # Business logic (Scoring, Auth, Activity, Analytics)
│   ├── agents/              # Multi-agent orchestrators (Planner, Coach, Analytics)
│   └── api/                 # REST endpoints
│       ├── health.py        # /api/v1/health
│       ├── auth.py          # /api/v1/auth (register, login, me)
│       ├── activities.py    # /api/v1/activities (batch, today, CRUD)
│       ├── goals.py         # /api/v1/goals (today, complete, CRUD)
│       ├── schedule.py      # /api/v1/schedule (today, generate, CRUD)
│       ├── analytics.py     # /api/v1/analytics (today, week, day)
│       ├── scoring.py       # /api/v1/score (today, events, history)
│       └── ai.py            # /api/v1/ai (chat, insights, plan)
├── .env.example             # Configuration template
├── pyproject.toml           # Project dependencies & packaging
└── README.md
```

---

## Getting Started

### 1. Prerequisites
- Python 3.12 or later
- PostgreSQL 15+ (optional; SQLite fallback available for local development)

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
pip install -e .
# or
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` and adjust the variables:
```bash
cp .env.example .env
```

Key configuration options:
```ini
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/dungeon_master
SECRET_KEY=generate-a-secure-random-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=60
OPENAI_API_KEY=sk-... # Optional, for live LLM agents
```

### 5. Run the Server
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- **Interactive API Docs (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

---

## Verified REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Service health status |
| `POST` | `/api/v1/auth/register` | Register new user account |
| `POST` | `/api/v1/auth/login` | Authenticate and obtain JWT token |
| `GET` | `/api/v1/auth/me` | Fetch active user profile |
| `POST` | `/api/v1/activities/batch` | Batch ingest foreground window activities |
| `GET` | `/api/v1/activities/today` | Fetch today's activity stream |
| `GET` | `/api/v1/goals` | List user objectives |
| `POST` | `/api/v1/goals` | Forge new quest |
| `POST` | `/api/v1/goals/{id}/complete`| Mark quest complete & award points |
| `GET` | `/api/v1/schedule/today` | Fetch active timetable |
| `POST` | `/api/v1/schedule/generate` | Trigger AI timetable orchestration |
| `GET` | `/api/v1/analytics/today` | Today's deep work & category breakdown |
| `GET` | `/api/v1/score/today` | Campaign score, streak, and rank |
| `GET` | `/api/v1/score/events` | Complete score audit trail |
| `POST` | `/api/v1/ai/chat` | Consult AI Dungeon Master Coach |
| `GET` | `/api/v1/ai/insights` | Fetch tactical AI observations |
