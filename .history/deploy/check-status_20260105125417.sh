#!/bin/bash

echo "=== Just A Bill - Service Status ==="
echo ""

cd /home/$USER/justabill

echo "Container Status:"
docker compose -f docker-compose.prod.yml ps

echo ""
echo "Disk Usage:"
df -h /

echo ""
echo "Docker Disk Usage:"
docker system df

echo ""
echo "Recent Logs (last 20 lines):"
docker compose -f docker-compose.prod.yml logs --tail=20

echo ""
echo "Health Check:"
curl -s http://localhost:8000/health | jq . || echo "Backend not responding"

echo ""
echo "Memory Usage:"
free -h
