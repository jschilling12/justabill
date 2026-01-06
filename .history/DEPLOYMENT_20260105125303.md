# Just A Bill - Production Deployment

This project is configured for automated deployment to AWS EC2 using GitHub Actions.

## Quick Links

- **[Quick Start Guide](docs/DEPLOYMENT_QUICKSTART.md)** - Get up and running in 15 minutes
- **[Full EC2 Deployment Guide](docs/EC2_DEPLOYMENT.md)** - Complete setup with SSL, monitoring, backups
- **[Local Development](README.md)** - Run locally with Docker Compose

## Deployment Overview

1. **EC2 Setup**: Launch Ubuntu instance, run setup script
2. **Environment Config**: Set production secrets in `.env`
3. **GitHub Actions**: Push to `main` → auto-deploys to EC2
4. **SSL (Optional)**: Configure domain + Let's Encrypt certificates

## Architecture

```
Internet → Nginx (80/443) → Frontend (Next.js, port 3000)
                          → Backend API (FastAPI, port 8000)
                              ↓
                          PostgreSQL + Redis
                              ↓
                          Celery Worker + n8n
```

## File Structure

```
deploy/
├── setup-ec2.sh          # Initial server setup
├── deploy-manual.sh      # Manual deployment
└── check-status.sh       # Health check script

.github/workflows/
└── deploy.yml            # Auto-deploy on push to main

nginx/
├── nginx.conf            # Nginx config
└── sites-enabled/
    └── justabill.conf    # Site routing config

docker-compose.prod.yml   # Production container config
.env.example              # Template for environment variables
```

## Requirements

- AWS EC2 instance (t3.medium recommended, 4 GB RAM minimum)
- Ubuntu 22.04 LTS
- Docker + Docker Compose
- Domain name (optional, for SSL)

## Security Notes

- All secrets in `.env` (never commit)
- SSH restricted to your IP
- Postgres/Redis not exposed publicly
- n8n accessible via SSH tunnel only
- HTTPS recommended for production

## Maintenance

```bash
# Check service health
./deploy/check-status.sh

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Restart service
docker compose -f docker-compose.prod.yml restart backend

# Database backup
docker compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U justabill justabill > backup_$(date +%Y%m%d).sql
```

## Cost Estimate

- EC2 t3.medium: ~$30/month
- Storage: ~$3/month
- **Total: ~$33/month** (use t3.small for ~$15/month on low traffic)

## Support

For issues or questions, see:
- [EC2 Deployment Troubleshooting](docs/EC2_DEPLOYMENT.md#part-6-troubleshooting)
- [GitHub Actions logs](../../actions)
