# Setup Instructions

## Prerequisites

- Docker and Docker Compose
- Congress.gov API key from [api.data.gov](https://api.data.gov/signup/)
- LLM API key (OpenAI or Anthropic)

## Quick Start

### 1. Clone and Setup

```powershell
cd "c:\Users\jorda\Dropbox\2021 - 2022\Programming\Git\justabill"

# Copy environment template
Copy-Item .env.example .env
```

### 2. Configure Environment

Edit `.env` and add your API keys:

```env
CONGRESS_API_KEY=your_congress_api_key_here
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
LLM_API_KEY=your_openai_api_key_here
```

### 3. Start Services

```powershell
# Start all services
docker-compose up -d

# Wait for services to be ready (about 30 seconds)
Start-Sleep -Seconds 30

# Check service status
docker-compose ps
```

### 4. Run Database Migrations

```powershell
docker-compose exec backend alembic upgrade head
```

### 5. Run Demo Script

```powershell
# Install httpx locally (if not already installed)
pip install httpx

# Run demo
python scripts/demo.py
```

### 6. Access Services

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **n8n**: http://localhost:5678 (user: admin, see .env for password)

## Manual Testing

### Ingest a Bill

```powershell
$body = @{
    congress = 118
    bill_type = "hr"
    bill_number = 1
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/ingest/bill" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

### List Bills

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/bills?page=1&page_size=10"
```

### Get Bill Details

```powershell
# Replace BILL_ID with actual bill ID
$billId = "your-bill-id-here"
Invoke-RestMethod -Uri "http://localhost:8000/bills/$billId"
```

### Submit a Vote

```powershell
$sessionId = [System.Guid]::NewGuid().ToString()
$body = @{
    section_id = "your-section-id-here"
    vote = "up"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/votes/vote?bill_id=your-bill-id-here" `
    -Method Post `
    -ContentType "application/json" `
    -Headers @{ "X-Session-ID" = $sessionId } `
    -Body $body
```

## Troubleshooting

### Backend won't start

```powershell
# Check logs
docker logs justabill-backend

# Common issues:
# 1. Database not ready - wait 30 seconds and retry
# 2. Port 8000 in use - change BACKEND_PORT in .env
```

### Worker not processing tasks

```powershell
# Check worker logs
docker logs justabill-worker

# Check Redis connection
docker exec justabill-redis redis-cli ping
```

### Frontend build errors

```powershell
# Rebuild frontend
docker-compose build frontend
docker-compose up -d frontend

# Check logs
docker logs justabill-frontend
```

### Database migration errors

```powershell
# Check current migration version
docker-compose exec backend alembic current

# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d postgres
Start-Sleep -Seconds 10
docker-compose up -d backend
docker-compose exec backend alembic upgrade head
```

## Development Workflow

### Run Backend Locally (without Docker)

```powershell
cd backend

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Set environment variables
$env:DATABASE_URL = "postgresql://justabill:justabill@localhost:5432/justabill"
$env:REDIS_URL = "redis://localhost:6379/0"

# Run migrations
alembic upgrade head

# Start backend
uvicorn app.main:app --reload --port 8000
```

### Run Tests

```powershell
docker-compose exec backend pytest
```

### View Logs

```powershell
# All services
docker-compose logs -f

# Specific service
docker logs -f justabill-backend
docker logs -f justabill-worker
docker logs -f justabill-frontend
```

### Restart Services

```powershell
# Restart specific service
docker-compose restart backend

# Restart all services
docker-compose restart
```

### Stop Services

```powershell
# Stop without removing volumes
docker-compose down

# Stop and remove volumes (deletes all data)
docker-compose down -v
```

## Production Deployment

See `DEPLOYMENT.md` for production deployment instructions.
