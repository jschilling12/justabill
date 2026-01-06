# Deployment Quick Start

Deploy Just A Bill to AWS EC2 with automatic updates on every GitHub push.

## 1. Launch EC2 Instance

- **Instance**: Ubuntu 22.04 LTS
- **Type**: t3.medium (2 vCPU, 4 GB RAM)
- **Storage**: 30 GB
- **Security Group**: Allow ports 22 (SSH), 80 (HTTP), 443 (HTTPS)

## 2. Initial Setup

```bash
# SSH into EC2
ssh -i your-key.pem ubuntu@YOUR_EC2_IP

# Download and run setup script
wget https://raw.githubusercontent.com/YOUR_USERNAME/justabill/main/deploy/setup-ec2.sh
chmod +x setup-ec2.sh
./setup-ec2.sh
```

## 3. Configure Environment

Edit `.env` file and set production values:

```bash
cd ~/justabill
nano .env
```

Required variables:
- `SECRET_KEY` - Generate with: `openssl rand -hex 32`
- `ADMIN_API_KEY` - Generate with: `openssl rand -base64 48`
- `POSTGRES_PASSWORD` - Strong password
- `LLM_API_KEY` - Your OpenAI/Anthropic key
- `CONGRESS_API_KEY` - From api.data.gov
- `NEXT_PUBLIC_API_URL` - `http://YOUR_IP/api` or `http://YOUR_DOMAIN/api`

## 4. Setup GitHub Auto-Deploy

In GitHub repo → Settings → Secrets, add:

| Secret         | Value                              |
|----------------|------------------------------------|
| `EC2_SSH_KEY`  | Contents of your `.pem` key file   |
| `EC2_HOST`     | Your EC2 IP or domain              |
| `EC2_USER`     | `ubuntu`                           |

## 5. Deploy!

Push to `main` branch:
```bash
git push origin main
```

GitHub Actions will automatically:
- Pull latest code on EC2
- Build containers
- Restart services
- Run migrations

## 6. Access Your App

- **Frontend**: `http://YOUR_EC2_IP`
- **Backend API**: `http://YOUR_EC2_IP/api`
- **n8n**: SSH tunnel required (see full docs)

## Common Commands

```bash
# SSH to server
ssh -i your-key.pem ubuntu@YOUR_EC2_IP

# Check status
cd ~/justabill && ./deploy/check-status.sh

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Manual deploy
./deploy/deploy-manual.sh

# Restart service
docker compose -f docker-compose.prod.yml restart backend
```

## Full Documentation

See [EC2_DEPLOYMENT.md](./EC2_DEPLOYMENT.md) for:
- SSL/HTTPS setup
- Domain configuration
- Database backups
- Monitoring & troubleshooting
- Security best practices

## Cost Estimate

- **t3.medium EC2**: ~$30/month
- **Storage (30 GB)**: ~$3/month
- **Total**: ~$33/month

Use `t3.small` for ~$15/month if traffic is low.
