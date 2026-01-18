#!/bin/bash
# Quick Production Deployment Script for BoA Exchange Rate API
# ============================================================

set -e  # Exit on error

echo "🚀 BoA Exchange Rate API - Production Deployment"
echo "================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root or with sudo${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1: System Update${NC}"
apt update && apt upgrade -y

echo -e "${GREEN}✓ System updated${NC}"
echo ""

echo -e "${YELLOW}Step 2: Installing Dependencies${NC}"
apt install -y docker.io docker-compose git curl vim nano htop

echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

echo -e "${YELLOW}Step 3: Starting Docker${NC}"
systemctl start docker
systemctl enable docker

echo -e "${GREEN}✓ Docker started${NC}"
echo ""

echo -e "${YELLOW}Step 4: Creating Application Directory${NC}"
mkdir -p /opt/boa-exchange-rate
cd /opt/boa-exchange-rate

echo -e "${GREEN}✓ Directory created${NC}"
echo ""

echo -e "${YELLOW}Step 5: Application Deployment${NC}"
echo ""
echo "Now you need to either:"
echo "1. Upload your application files to /opt/boa-exchange-rate"
echo "2. Clone from git repository"
echo ""
echo "After uploading files, run:"
echo "  cd /opt/boa-exchange-rate"
echo "  cp config/.env.production config/.env"
echo "  nano config/.env  # Edit with your values"
echo "  mkdir -p data logs static"
echo "  docker-compose up -d --build"
echo ""
echo -e "${GREEN}✓ Server is ready for deployment${NC}"
echo ""

echo -e "${YELLOW}Step 6: Firewall Configuration${NC}"
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8000/tcp
ufw --force enable

echo -e "${GREEN}✓ Firewall configured${NC}"
echo ""

echo "🎉 Server preparation complete!"
echo ""
echo "Next steps:"
echo "1. Upload your application code"
echo "2. Configure config/.env with production values"
echo "3. Run: docker-compose up -d --build"
echo "4. Setup SSL certificate with Certbot"
echo ""
echo "See PRODUCTION_DEPLOYMENT.md for detailed instructions."
