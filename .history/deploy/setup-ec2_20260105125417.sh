#!/bin/bash
set -e

echo "=== Just A Bill - Initial EC2 Setup Script ==="
echo "This script will set up the production environment on a fresh EC2 instance."
echo ""

# Check if running as non-root user
if [ "$EUID" -eq 0 ]; then 
   echo "Please run as a non-root user with sudo privileges"
   exit 1
fi

echo "=== Step 1: Update system packages ==="
sudo apt-get update
sudo apt-get upgrade -y

echo "=== Step 2: Install Docker ==="
if ! command -v docker &> /dev/null; then
    # Install Docker
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "Docker installed. You may need to log out and back in for group changes to take effect."
else
    echo "Docker already installed"
fi

echo "=== Step 3: Install Docker Compose ==="
if ! command -v docker &> /dev/null || ! docker compose version &> /dev/null; then
    sudo apt-get install -y docker-compose-plugin
else
    echo "Docker Compose already installed"
fi

echo "=== Step 4: Install Git ==="
if ! command -v git &> /dev/null; then
    sudo apt-get install -y git
else
    echo "Git already installed"
fi

echo "=== Step 5: Clone repository ==="
if [ ! -d "$HOME/justabill" ]; then
    read -p "Enter your GitHub repository URL: " REPO_URL
    git clone $REPO_URL $HOME/justabill
else
    echo "Repository already cloned at $HOME/justabill"
fi

cd $HOME/justabill

echo "=== Step 6: Create .env file ==="
if [ ! -f .env ]; then
    echo "Creating .env from example..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and set your production values!"
    echo "   Key variables to set:"
    echo "   - SECRET_KEY (generate a strong random key)"
    echo "   - POSTGRES_PASSWORD"
    echo "   - ADMIN_API_KEY"
    echo "   - LLM_API_KEY"
    echo "   - CONGRESS_API_KEY"
    echo "   - N8N_BASIC_AUTH_PASSWORD"
    echo ""
    read -p "Press Enter to open .env in nano editor..." 
    nano .env
else
    echo ".env file already exists"
fi

echo "=== Step 7: Create required directories ==="
mkdir -p $HOME/justabill/nginx/ssl

echo "=== Step 8: Set up firewall ==="
if command -v ufw &> /dev/null; then
    sudo ufw allow 22/tcp    # SSH
    sudo ufw allow 80/tcp    # HTTP
    sudo ufw allow 443/tcp   # HTTPS
    sudo ufw --force enable
    echo "Firewall configured"
else
    echo "⚠️  UFW not found. Configure your EC2 Security Group manually:"
    echo "   - Allow SSH (22) from your IP"
    echo "   - Allow HTTP (80) from anywhere"
    echo "   - Allow HTTPS (443) from anywhere"
fi

echo "=== Step 9: Build and start containers ==="
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

echo "=== Step 10: Wait for services to start ==="
sleep 15

echo "=== Step 11: Run database migrations ==="
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head

echo "=== Step 12: Check service status ==="
docker compose -f docker-compose.prod.yml ps

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Next steps:"
echo "1. Configure your domain DNS to point to this EC2 instance"
echo "2. Set up SSL certificates (see docs/SSL_SETUP.md)"
echo "3. Configure GitHub repository secrets for auto-deployment:"
echo "   - EC2_SSH_KEY: Your private SSH key"
echo "   - EC2_HOST: EC2 instance public IP or domain"
echo "   - EC2_USER: $USER"
echo ""
echo "Access your services:"
echo "  - Frontend: http://$(curl -s http://checkip.amazonaws.com)"
echo "  - Backend API: http://$(curl -s http://checkip.amazonaws.com)/api"
echo "  - n8n: http://localhost:5678 (SSH tunnel required)"
echo ""
echo "View logs:"
echo "  docker compose -f docker-compose.prod.yml logs -f"
echo ""
