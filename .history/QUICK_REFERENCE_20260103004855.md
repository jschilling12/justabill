# Just A Bill - Quick Reference

## 🚀 One-Command Start

```powershell
docker-compose up -d && Start-Sleep -Seconds 30 && docker-compose exec backend alembic upgrade head && python scripts/demo.py
```

## 🔗 Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | None |
| Backend API | http://localhost:8000 | None |
| API Docs | http://localhost:8000/docs | None |
| n8n | http://localhost:5678 | admin / (see .env) |
| PostgreSQL | localhost:5432 | justabill / justabill |
| Redis | localhost:6379 | None |

## 📝 Common Commands

### Docker

```powershell
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
docker logs -f justabill-backend
docker logs -f justabill-worker

# Restart a service
docker-compose restart backend

# Stop all services
docker-compose down

# Stop and remove all data
docker-compose down -v

# Check status
docker-compose ps
```

### Database

```powershell
# Run migrations
docker-compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "description"

# Rollback migration
docker-compose exec backend alembic downgrade -1

# Connect to database
docker exec -it justabill-postgres psql -U justabill -d justabill
```

### Testing

```powershell
# Run all tests
docker-compose exec backend pytest

# Run with coverage
docker-compose exec backend pytest --cov=app

# Run specific test
docker-compose exec backend pytest tests/test_sectioning.py -v
```

### API Testing

```powershell
# Health check
Invoke-RestMethod http://localhost:8000/health

# List bills
Invoke-RestMethod http://localhost:8000/bills

# Get bill
$billId = "your-bill-id"
Invoke-RestMethod "http://localhost:8000/bills/$billId"

# Ingest bill
$body = @{ congress=118; bill_type="hr"; bill_number=1 } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/ingest/bill -Method Post -ContentType "application/json" -Body $body
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Port already in use | Change port in .env or stop conflicting service |
| Database connection error | Wait 30s after `docker-compose up`, then retry |
| Worker not processing | Check: `docker logs justabill-worker`, verify Redis is running |
| Frontend 404 error | Frontend takes ~60s to build on first start |
| Congress API 429 error | Rate limited - wait 60s or request higher limit |
| LLM API error | Verify API key in .env and credits/quota |

## 📊 Key Metrics

| Metric | Value |
|--------|-------|
| Startup Time | ~60 seconds |
| Bill Ingestion Time | ~10-30 seconds |
| Section Summarization | ~5-15 seconds each |
| Support Score Calculation | <1 second |

## 🔑 Required Environment Variables

```env
# Required
CONGRESS_API_KEY=xxx        # Get from api.data.gov
LLM_PROVIDER=openai         # or anthropic, local
LLM_API_KEY=xxx             # OpenAI or Anthropic key
LLM_MODEL=gpt-4             # or gpt-3.5-turbo, claude-3-opus-20240229

# Optional (have defaults)
DATABASE_URL=postgresql://justabill:justabill@postgres:5432/justabill
REDIS_URL=redis://redis:6379/0
N8N_BASIC_AUTH_PASSWORD=changeme
```

## 🎯 Demo Flow

1. **Start**: `docker-compose up -d`
2. **Migrate**: `docker-compose exec backend alembic upgrade head`
3. **Demo**: `python scripts/demo.py`
4. **Browse**: Open http://localhost:3000
5. **Vote**: Click a bill, vote on sections
6. **Summary**: Click "View My Summary"

## 🔥 Quick Ingest

```powershell
# Ingest HR 1 from 118th Congress
$body = @{ congress=118; bill_type="hr"; bill_number=1 } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/ingest/bill -Method Post -ContentType "application/json" -Body $body

# Wait for summarization (check logs)
docker logs -f justabill-worker

# View in browser
Start-Process "http://localhost:3000"
```

## 📚 Documentation

- **Architecture**: [README.md](README.md)
- **Setup Guide**: [SETUP.md](SETUP.md)
- **File Structure**: [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
- **Implementation Details**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- **n8n Workflows**: [n8n/README.md](n8n/README.md)

## 🎓 Learning Resources

- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy: https://docs.sqlalchemy.org/
- Celery: https://docs.celeryq.dev/
- Next.js: https://nextjs.org/docs
- n8n: https://docs.n8n.io/
- Congress API: https://github.com/LibraryOfCongress/api.congress.gov

## ⚡ Pro Tips

1. **Use Docker logs**: Most issues are visible in service logs
2. **Check health endpoint**: `curl http://localhost:8000/health`
3. **Monitor Celery**: Worker logs show summarization progress
4. **Use API docs**: Interactive API testing at `/docs`
5. **n8n workflows**: Test manually before activating cron triggers

## 🎉 Success Indicators

✅ `docker-compose ps` shows all services "Up"
✅ `http://localhost:8000/health` returns 200 OK
✅ Frontend loads at `http://localhost:3000`
✅ Demo script completes without errors
✅ Bills appear in frontend after ingestion
✅ Votes submit successfully
✅ User summary shows correct verdict

---

**Need help?** Check [SETUP.md](SETUP.md) for detailed troubleshooting or the logs:
```powershell
docker-compose logs -f
```
