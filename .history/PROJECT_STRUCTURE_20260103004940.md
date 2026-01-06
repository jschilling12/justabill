# Project File Tree

```
justabill/
├── .env.example                    # Environment variables template
├── .gitignore                      # Git ignore rules
├── docker-compose.yml              # Docker services configuration
├── README.md                       # Project overview and documentation
├── SETUP.md                        # Setup instructions
│
├── .github/
│   └── agents/
│       └── imjustabillinfastructure.agent.md  # VS Code agent configuration
│
├── backend/                        # FastAPI backend service
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── alembic.ini                 # Alembic configuration
│   │
│   ├── alembic/                    # Database migrations
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 001_initial_migration.py
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application entry
│   │   ├── config.py               # Settings and configuration
│   │   ├── database.py             # Database connection
│   │   ├── models.py               # SQLAlchemy models
│   │   ├── schemas.py              # Pydantic schemas
│   │   ├── celery_app.py           # Celery configuration
│   │   ├── tasks.py                # Background tasks
│   │   ├── llm_client.py           # LLM abstraction layer
│   │   ├── congress_client.py      # Congress API client
│   │   │
│   │   ├── routers/                # API endpoints
│   │   │   ├── __init__.py
│   │   │   ├── health.py
│   │   │   ├── bills.py
│   │   │   ├── ingestion.py
│   │   │   └── votes.py
│   │   │
│   │   └── services/               # Business logic
│   │       ├── __init__.py
│   │       └── vote_service.py
│   │
│   └── tests/                      # Unit tests
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_sectioning.py
│       └── test_vote_service.py
│
├── frontend/                       # Next.js frontend
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.js
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   │
│   ├── lib/
│   │   └── api.ts                  # API client
│   │
│   ├── pages/
│   │   ├── _app.tsx
│   │   ├── _document.tsx
│   │   ├── index.tsx               # Bills list page
│   │   └── bills/
│   │       └── [id].tsx            # Bill detail page
│   │
│   └── styles/
│       └── globals.css
│
├── n8n/                            # n8n workflows
│   ├── README.md                   # Workflow documentation
│   └── workflows/
│       ├── daily-bill-sync.json
│       └── resummarize-bill.json
│
└── scripts/                        # Utility scripts
    └── demo.py                     # Demo script

```

## Key Files Explained

### Configuration
- **`.env.example`**: Template for environment variables (API keys, database URLs)
- **`docker-compose.yml`**: Orchestrates all services (Postgres, Redis, Backend, Worker, n8n, Frontend)

### Backend
- **`app/main.py`**: FastAPI app initialization, CORS, exception handlers
- **`app/models.py`**: Database schema (Bills, Sections, Users, Votes, Summaries)
- **`app/congress_client.py`**: Congress.gov API integration + bill sectioning
- **`app/llm_client.py`**: LLM provider abstraction (OpenAI/Anthropic/Local)
- **`app/tasks.py`**: Celery tasks for async summarization
- **`app/routers/`**: REST API endpoints
  - `bills.py`: List bills, get bill details, user summaries
  - `ingestion.py`: Ingest bills from Congress.gov
  - `votes.py`: Submit and retrieve votes
- **`app/services/vote_service.py`**: Vote aggregation and support score calculation

### Frontend
- **`pages/index.tsx`**: Home page with bills list
- **`pages/bills/[id].tsx`**: Bill detail page with voting interface
- **`lib/api.ts`**: API client with session management

### Database
- **`alembic/versions/001_*.py`**: Initial database schema migration

### Workflows
- **`n8n/workflows/daily-bill-sync.json`**: Automated daily bill ingestion
- **`n8n/workflows/resummarize-bill.json`**: On-demand re-summarization

### Scripts
- **`scripts/demo.py`**: Automated demo to ingest sample bills and test the system

## Services Overview

| Service | Port | Purpose |
|---------|------|---------|
| Backend | 8000 | REST API |
| Frontend | 3000 | Web UI |
| n8n | 5678 | Workflow automation |
| Postgres | 5432 | Database |
| Redis | 6379 | Cache & message broker |
| Worker | - | Background task processing |

## Data Flow

1. **Ingestion**: n8n → Backend `/ingest/bill` → Fetch from Congress.gov → Parse & section → Queue summarization
2. **Summarization**: Celery Worker → LLM → Store summary + evidence → Update database
3. **Voting**: User → Frontend → Backend `/votes/vote` → Store vote → Invalidate cached summary
4. **Recap**: Frontend → Backend `/bills/{id}/user-summary` → Calculate support score → Return verdict + liked/disliked sections

## Key Metrics

- **Lines of Code**: ~3,500
- **API Endpoints**: 10+
- **Database Tables**: 6
- **LLM Providers Supported**: 3 (OpenAI, Anthropic, Local)
- **Deployment Time**: ~5 minutes
- **Test Coverage**: Core business logic (sectioning, vote aggregation)
