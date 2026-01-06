# EC2 Deployment - Setup Complete ✅

Your repository is now configured for automated deployment to AWS EC2!

## What Was Set Up

### 1. Production Infrastructure
- ✅ `docker-compose.prod.yml` - Production container config with Nginx reverse proxy
- ✅ `nginx/` - Nginx config with HTTP/HTTPS routing
- ✅ `frontend/Dockerfile.prod` - Optimized Next.js production build

### 2. Automated Deployment
- ✅ `.github/workflows/deploy.yml` - GitHub Actions workflow that auto-deploys on push to `main`
- ✅ Deployment triggers: Pull code → Build → Restart → Migrate → Verify

### 3. Deployment Scripts
- ✅ `deploy/setup-ec2.sh` - Initial EC2 server setup (run once)
- ✅ `deploy/deploy-manual.sh` - Manual deployment script
- ✅ `deploy/check-status.sh` - Health check and monitoring

### 4. Documentation
- ✅ `DEPLOYMENT.md` - Main deployment overview
- ✅ `docs/DEPLOYMENT_QUICKSTART.md` - 15-minute quick start
- ✅ `docs/EC2_DEPLOYMENT.md` - Complete guide with SSL, backups, troubleshooting

## Next Steps

### 1. Launch EC2 Instance
```bash
# Recommended specs:
# - Ubuntu 22.04 LTS
# - t3.medium (2 vCPU, 4 GB RAM)
# - 30 GB storage
# - Security Group: Allow ports 22, 80, 443
```

### 2. Run Setup Script on EC2
```bash
# Copy script to EC2
scp -i your-key.pem deploy/setup-ec2.sh ubuntu@YOUR_EC2_IP:~/

# SSH and run
ssh -i your-key.pem ubuntu@YOUR_EC2_IP
chmod +x setup-ec2.sh
./setup-ec2.sh
```

The script will:
- Install Docker + Git
- Clone your repo
- Create `.env` file
- Build containers
- Start services

### 3. Configure Secrets

**On EC2 (`.env` file):**
```bash
cd ~/justabill
nano .env

# Set these production values:
SECRET_KEY=<generate with: openssl rand -hex 32>
ADMIN_API_KEY=<generate with: openssl rand -base64 48>
POSTGRES_PASSWORD=<strong password>
LLM_API_KEY=<your OpenAI/Anthropic key>
CONGRESS_API_KEY=<from api.data.gov>
NEXT_PUBLIC_API_URL=http://YOUR_DOMAIN/api  # or http://YOUR_EC2_IP/api
```

**In GitHub (Settings → Secrets → Actions):**
| Secret        | Value                           |
|---------------|---------------------------------|
| `EC2_SSH_KEY` | Contents of your `.pem` file    |
| `EC2_HOST`    | Your EC2 IP or domain           |
| `EC2_USER`    | `ubuntu`                        |

### 4. Test Auto-Deployment
```bash
# Make a small change
git add .
git commit -m "Test deployment"
git push origin main

# Watch deployment in GitHub → Actions tab
# After ~2-3 minutes, check: http://YOUR_EC2_IP
```

### 5. (Optional) Set Up SSL/HTTPS
```bash
# Point your domain to EC2 IP
# SSH into EC2 and run:
sudo certbot certonly --standalone -d yourdomain.com
sudo cp /etc/letsencrypt/live/yourdomain.com/*.pem ~/justabill/nginx/ssl/

# Edit nginx config and uncomment HTTPS server block
nano ~/justabill/nginx/sites-enabled/justabill.conf

# Restart nginx
docker compose -f docker-compose.prod.yml restart nginx
```

## Architecture

```
Internet
   ↓
Nginx (port 80/443)
   ├─→ Frontend (Next.js, port 3000)
   └─→ Backend API (FastAPI, port 8000)
          ↓
       PostgreSQL + Redis
          ↓
       Celery Worker + n8n
```

## Cost Estimate

- **EC2 t3.medium**: ~$30/month
- **30 GB storage**: ~$3/month
- **Total**: ~$33/month

(Use t3.small for ~$15/month if low traffic)

## Common Commands

```bash
# SSH to server
ssh -i your-key.pem ubuntu@YOUR_EC2_IP

# Check service status
cd ~/justabill && ./deploy/check-status.sh

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Restart service
docker compose -f docker-compose.prod.yml restart backend

# Manual deploy
./deploy/deploy-manual.sh
```

## Security Checklist

- [ ] SSH restricted to your IP only (EC2 Security Group)
- [ ] Strong passwords set in `.env`
- [ ] `SECRET_KEY` and `ADMIN_API_KEY` are random/unique
- [ ] SSL/HTTPS enabled (for production with domain)
- [ ] `.env` not committed to Git (already in `.gitignore`)
- [ ] GitHub secrets configured (EC2_SSH_KEY, EC2_HOST, EC2_USER)

## Testing the Deployment

After setup:
1. **Frontend**: Visit `http://YOUR_EC2_IP`
2. **Backend API**: Visit `http://YOUR_EC2_IP/api/health`
3. **Check logs**: `docker compose -f docker-compose.prod.yml logs -f`

## Full Documentation

- Quick start: [docs/DEPLOYMENT_QUICKSTART.md](docs/DEPLOYMENT_QUICKSTART.md)
- Complete guide: [docs/EC2_DEPLOYMENT.md](docs/EC2_DEPLOYMENT.md)
- Main overview: [DEPLOYMENT.md](DEPLOYMENT.md)

## Troubleshooting

**Services won't start:**
```bash
docker compose -f docker-compose.prod.yml logs
```

**Out of disk space:**
```bash
docker system prune -a
```

**GitHub Actions deploy fails:**
- Check GitHub Actions logs
- Verify EC2_SSH_KEY, EC2_HOST, EC2_USER secrets
- Test SSH manually: `ssh -i your-key.pem ubuntu@YOUR_EC2_IP`

---

**Ready to deploy?** Start with step 1 above or see the [Quick Start Guide](docs/DEPLOYMENT_QUICKSTART.md).
