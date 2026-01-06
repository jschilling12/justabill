#!/bin/bash
set -e

echo "=== Manual Deployment Script ==="
echo "Use this for manual deployments or troubleshooting"
echo ""

cd /home/$USER/justabill

echo "Step 1: Pull latest code"
git fetch origin
git reset --hard origin/main

echo "Step 2: Build containers"
docker compose -f docker-compose.prod.yml build --no-cache

echo "Step 3: Stop existing containers"
docker compose -f docker-compose.prod.yml down

echo "Step 4: Start new containers"
docker compose -f docker-compose.prod.yml up -d

echo "Step 5: Wait for services"
sleep 10

echo "Step 6: Run migrations"
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head || echo "Migration skipped"

echo "Step 7: Check status"
docker compose -f docker-compose.prod.yml ps

echo "Step 8: Test health endpoint"
curl -f http://localhost:8000/health || echo "⚠️  Health check failed"

echo ""
echo "Deployment complete!"
echo "View logs: docker compose -f docker-compose.prod.yml logs -f"
