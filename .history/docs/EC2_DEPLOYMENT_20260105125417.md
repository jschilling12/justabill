# EC2 Deployment Guide

This guide covers deploying Just A Bill to an AWS EC2 instance with automatic deployment from GitHub.

## Overview

- **Infrastructure**: AWS EC2 (Ubuntu)
- **Containers**: Docker + Docker Compose
- **Reverse Proxy**: Nginx
- **CI/CD**: GitHub Actions
- **Services**: Backend (FastAPI), Frontend (Next.js), PostgreSQL, Redis, Celery, n8n

## Prerequisites

1. AWS account with EC2 access
2. Domain name (optional, but recommended for production)
3. GitHub repository with admin access

---

## Part 1: EC2 Instance Setup

### 1.1 Launch EC2 Instance

**Recommended specs:**
- **Instance Type**: `t3.medium` or larger (2 vCPU, 4 GB RAM minimum)
- **OS**: Ubuntu 22.04 LTS
- **Storage**: 20 GB minimum (30+ GB recommended)
- **Region**: Choose closest to your users

**Steps:**
1. Go to AWS EC2 Console
2. Click "Launch Instance"
3. Choose Ubuntu Server 22.04 LTS (64-bit x86)
4. Select instance type (t3.medium recommended)
5. Configure storage (20-30 GB)
6. **Create/select a key pair** (save the `.pem` file securely)

### 1.2 Configure Security Group

Create or configure security group with these rules:

| Type  | Protocol | Port | Source    | Description          |
|-------|----------|------|-----------|----------------------|
| SSH   | TCP      | 22   | Your IP   | SSH access           |
| HTTP  | TCP      | 80   | 0.0.0.0/0 | Public web access    |
| HTTPS | TCP      | 443  | 0.0.0.0/0 | Secure web access    |

**Important**: Restrict SSH (port 22) to your IP address only.

### 1.3 Allocate Elastic IP (Recommended)

To prevent your IP from changing on instance restart:
1. Go to EC2 → Elastic IPs
2. Click "Allocate Elastic IP address"
3. Associate it with your EC2 instance

### 1.4 Connect to EC2

```bash
# Change permissions on your key file
chmod 400 your-key.pem

# Connect via SSH
ssh -i your-key.pem ubuntu@YOUR_EC2_IP
```

---

## Part 2: Initial Server Setup

### 2.1 Run Setup Script

Copy the setup script to your EC2 instance:

```bash
# On your local machine
scp -i your-key.pem deploy/setup-ec2.sh ubuntu@YOUR_EC2_IP:~/

# SSH into EC2
ssh -i your-key.pem ubuntu@YOUR_EC2_IP

# Make script executable and run
chmod +x setup-ec2.sh
./setup-ec2.sh
```

The script will:
- Install Docker & Docker Compose
- Install Git
- Clone your repository
- Create `.env` file
- Configure firewall
- Build and start containers

### 2.2 Configure Environment Variables

Edit `.env` file with production values:

```bash
cd ~/justabill
nano .env
```

**Critical variables to set:**

```env
# Generate a strong secret key (32+ random characters)
SECRET_KEY=YOUR_PRODUCTION_SECRET_HERE

# Database credentials
POSTGRES_USER=justabill
POSTGRES_PASSWORD=STRONG_PASSWORD_HERE
POSTGRES_DB=justabill

# Admin API key for automation endpoints
ADMIN_API_KEY=STRONG_RANDOM_KEY_HERE

# LLM API (OpenAI, Anthropic, etc.)
LLM_PROVIDER=openai
LLM_API_KEY=your_openai_api_key_here
LLM_MODEL=gpt-3.5-turbo

# Congress.gov API
CONGRESS_API_KEY=your_congress_api_key_here

# n8n authentication
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=STRONG_PASSWORD_HERE

# Frontend public API URL (use your domain or EC2 IP)
NEXT_PUBLIC_API_URL=http://YOUR_DOMAIN_OR_IP/api
```

**Generate strong secrets:**
```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate ADMIN_API_KEY
openssl rand -base64 48
```

---

## Part 3: GitHub Actions Setup

### 3.1 Add GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions

Add these secrets:

| Secret Name    | Value                                           |
|----------------|-------------------------------------------------|
| `EC2_SSH_KEY`  | Contents of your `.pem` key file                |
| `EC2_HOST`     | Your EC2 public IP or domain                    |
| `EC2_USER`     | `ubuntu` (or your EC2 username)                 |

**To get EC2_SSH_KEY value:**
```bash
cat your-key.pem
```
Copy the entire contents (including `-----BEGIN` and `-----END` lines).

### 3.2 Configure SSH Key on EC2

Ensure the GitHub Actions runner can access your EC2:

```bash
# On EC2, ensure your user's authorized_keys is set up
cat ~/.ssh/authorized_keys
# Should contain the public key matching your .pem file
```

### 3.3 Test Auto-Deployment

1. Make a small change to your code
2. Commit and push to `main` branch:
   ```bash
   git add .
   git commit -m "Test deployment"
   git push origin main
   ```
3. Go to GitHub → Actions tab
4. Watch the deployment workflow run
5. Verify deployment succeeded

---

## Part 4: Domain & SSL Setup (Optional but Recommended)

### 4.1 Point Domain to EC2

In your domain registrar (e.g., Namecheap, GoDaddy, Route 53):
1. Create an A record pointing to your EC2 Elastic IP
2. Example: `justabill.yourdomain.com` → `YOUR_EC2_IP`

### 4.2 Install Certbot (Let's Encrypt SSL)

```bash
# SSH into EC2
ssh -i your-key.pem ubuntu@YOUR_EC2_IP

# Install Certbot
sudo apt-get update
sudo apt-get install -y certbot

# Stop nginx temporarily
cd ~/justabill
docker compose -f docker-compose.prod.yml stop nginx

# Obtain certificate
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Copy certificates to nginx directory
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ~/justabill/nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ~/justabill/nginx/ssl/
sudo chown $USER:$USER ~/justabill/nginx/ssl/*.pem

# Restart nginx
docker compose -f docker-compose.prod.yml start nginx
```

### 4.3 Enable HTTPS in Nginx

Edit `nginx/sites-enabled/justabill.conf`:

```bash
nano ~/justabill/nginx/sites-enabled/justabill.conf
```

Uncomment the HTTPS server block and update `server_name` with your domain.

Restart nginx:
```bash
docker compose -f docker-compose.prod.yml restart nginx
```

### 4.4 Auto-Renew SSL Certificates

```bash
# Add cron job for auto-renewal
sudo crontab -e

# Add this line (runs daily at 2 AM)
0 2 * * * certbot renew --quiet --deploy-hook "docker restart justabill-nginx"
```

---

## Part 5: Monitoring & Maintenance

### 5.1 Check Service Status

```bash
cd ~/justabill
./deploy/check-status.sh
```

### 5.2 View Logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f backend

# Last 100 lines
docker compose -f docker-compose.prod.yml logs --tail=100
```

### 5.3 Manual Deployment

If GitHub Actions deployment fails:

```bash
cd ~/justabill
./deploy/deploy-manual.sh
```

### 5.4 Database Backups

```bash
# Create backup
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U justabill justabill > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
docker compose -f docker-compose.prod.yml exec -T postgres psql -U justabill justabill < backup_20260105_120000.sql
```

### 5.5 Update Environment Variables

```bash
# Edit .env
nano ~/justabill/.env

# Restart affected services
docker compose -f docker-compose.prod.yml restart backend worker
```

---

## Part 6: Troubleshooting

### Services won't start

```bash
# Check container logs
docker compose -f docker-compose.prod.yml logs

# Check specific service
docker compose -f docker-compose.prod.yml logs backend

# Restart all services
docker compose -f docker-compose.prod.yml restart
```

### Out of disk space

```bash
# Clean up Docker
docker system prune -a

# Clean up old images
docker image prune -a

# Check disk usage
df -h
docker system df
```

### Database connection issues

```bash
# Check postgres is running
docker compose -f docker-compose.prod.yml ps postgres

# Test connection
docker compose -f docker-compose.prod.yml exec postgres psql -U justabill -d justabill -c "SELECT 1;"
```

### Frontend can't reach backend

Check `NEXT_PUBLIC_API_URL` in `.env`:
- Should be `http://YOUR_DOMAIN/api` or `http://YOUR_IP/api`
- Must be accessible from user's browser (not `localhost`)

---

## Part 7: Security Checklist

- [ ] SSH restricted to your IP only
- [ ] Strong passwords for all services (Postgres, n8n)
- [ ] `SECRET_KEY` is random and unique
- [ ] SSL/HTTPS enabled (if using domain)
- [ ] `.env` file not committed to Git
- [ ] Regular backups configured
- [ ] OS security updates enabled:
  ```bash
  sudo apt-get update && sudo apt-get upgrade -y
  ```
- [ ] Monitor logs for suspicious activity

---

## Part 8: Cost Optimization

**Estimated monthly costs (AWS us-east-1):**
- `t3.medium` EC2: ~$30/month
- 30 GB EBS storage: ~$3/month
- Elastic IP: Free (when attached)
- Data transfer: Varies (~$0.09/GB)

**To reduce costs:**
- Use `t3.small` for low traffic (~$15/month)
- Stop instance when not in use (dev/testing)
- Use AWS free tier eligible instance for first year

---

## Quick Reference

### Useful Commands

```bash
# SSH into EC2
ssh -i your-key.pem ubuntu@YOUR_EC2_IP

# Check all services
cd ~/justabill && docker compose -f docker-compose.prod.yml ps

# Restart specific service
docker compose -f docker-compose.prod.yml restart backend

# View logs
docker compose -f docker-compose.prod.yml logs -f backend

# Manual deploy
cd ~/justabill && ./deploy/deploy-manual.sh

# Database backup
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U justabill justabill > backup.sql
```

### Important Files

- `.env` - Environment variables (SECRET_KEY, passwords, API keys)
- `docker-compose.prod.yml` - Production container config
- `nginx/sites-enabled/justabill.conf` - Web server config
- `.github/workflows/deploy.yml` - Auto-deployment config

---

## Support

If you encounter issues:
1. Check logs: `docker compose -f docker-compose.prod.yml logs`
2. Verify `.env` variables are set correctly
3. Ensure security group allows traffic on ports 80/443
4. Check GitHub Actions logs for deployment failures
