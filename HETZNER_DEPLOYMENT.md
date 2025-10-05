# Hetzner Server Deployment - Step by Step Guide

## Server: ubuntu-4gb-fsn1-2 (IPv6: 2a01:4f8:c013:3866::/64)

### Prerequisites Verification

Access your server through Hetzner Cloud Console:
1. Go to https://console.hetzner.cloud/
2. Click on your server "ubuntu-4gb-fsn1-2"
3. Click "Console" button to open web terminal

### Step 1: System Setup

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y docker.io docker-compose git curl vim nano

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add current user to docker group (to run docker without sudo)
sudo usermod -aG docker $USER

# Verify Docker installation
docker --version
docker-compose --version

# Log out and back in, or run:
newgrp docker
```

### Step 2: Create Project Directory

```bash
# Create application directory
sudo mkdir -p /opt/boa-exchange-rate
sudo chown $USER:$USER /opt/boa-exchange-rate
cd /opt/boa-exchange-rate
```

### Step 3: Get the Code

**Once GitHub repo is ready, you'll run:**
```bash
# Clone the repository (replace with actual GitHub URL)
git clone https://github.com/YOUR_USERNAME/boa-exchange-rate-api.git .

# Or if using the bundle file:
# Upload boa-exchange-rate.bundle to server first, then:
# git clone boa-exchange-rate.bundle .
```

### Step 4: Environment Configuration

```bash
# Create logs directory
mkdir -p logs

# Copy example environment file
cp config/.env.example config/.env

# Edit environment file with your settings
nano config/.env
```

**Required .env configuration:**
```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
LOG_LEVEL=INFO

# QuickBooks Configuration (get these from QuickBooks Developer Dashboard)
QB_CLIENT_ID=your_actual_quickbooks_client_id
QB_CLIENT_SECRET=your_actual_quickbooks_client_secret
QB_REDIRECT_URI=https://your-domain.com/auth/callback
QB_ENVIRONMENT=sandbox
QB_BASE_URL=https://sandbox-quickbooks.api.intuit.com

# Security (generate a strong secret key)
SECRET_KEY=your-very-secure-secret-key-minimum-32-characters-long

# Scheduler Configuration
EXCHANGE_RATE_UPDATE_INTERVAL=3600
QUICKBOOKS_SYNC_INTERVAL=86400

# Logging
LOG_FILE=logs/boa_api.log
LOG_MAX_SIZE=10485760
LOG_BACKUP_COUNT=5

# Application Settings
APP_NAME=BoA Exchange Rate API
APP_VERSION=1.0.0
CORS_ORIGINS=*
RATE_LIMIT=100
```

### Step 5: Deploy with Docker

```bash
# Build and start the application
docker-compose up -d

# Check if containers are running
docker-compose ps

# View logs
docker-compose logs -f boa-api
```

### Step 6: Test the API

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test exchange rates endpoint
curl http://localhost:8000/api/v1/exchange-rates

# Test API documentation
curl http://localhost:8000/docs
```

### Step 7: Configure Firewall (IPv6)

```bash
# Check current firewall status
sudo ufw status

# Allow HTTP and HTTPS (if using Nginx)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow API port (if accessing directly)
sudo ufw allow 8000/tcp

# Enable firewall (if not already enabled)
sudo ufw --force enable
```

### Step 8: Set Up Domain/SSL (Optional)

If you have a domain pointing to your server:

```bash
# Install Certbot for Let's Encrypt SSL
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate (replace with your domain)
sudo certbot --nginx -d yourdomain.com

# Test SSL renewal
sudo certbot renew --dry-run
```

### Management Commands

```bash
# View application logs
docker-compose logs boa-api

# View all container logs
docker-compose logs

# Restart the application
docker-compose restart boa-api

# Stop the application
docker-compose down

# Update the application (after git pull)
git pull
docker-compose down
docker-compose up -d --build

# Check container resource usage
docker stats

# Access container shell (for debugging)
docker-compose exec boa-api /bin/bash
```

### Troubleshooting

1. **Container won't start:**
   ```bash
   docker-compose logs boa-api
   docker-compose ps
   ```

2. **Port conflicts:**
   ```bash
   sudo netstat -tlnp | grep 8000
   sudo lsof -i :8000
   ```

3. **Permission issues:**
   ```bash
   sudo chown -R $USER:$USER /opt/boa-exchange-rate
   ```

4. **Docker permission denied:**
   ```bash
   sudo usermod -aG docker $USER
   newgrp docker
   ```

5. **IPv6 connectivity issues:**
   ```bash
   # Test IPv6 connectivity
   ping6 google.com
   
   # Check IPv6 configuration
   ip -6 addr show
   ```

### Monitoring and Maintenance

1. **Set up log rotation:**
   ```bash
   sudo nano /etc/logrotate.d/boa-api
   ```

2. **Monitor disk space:**
   ```bash
   df -h
   docker system prune -f  # Clean up unused Docker data
   ```

3. **Set up auto-updates (optional):**
   ```bash
   # Create update script
   nano /home/$USER/update-boa-api.sh
   chmod +x /home/$USER/update-boa-api.sh
   
   # Add to crontab for daily updates
   crontab -e
   # Add: 0 2 * * * /home/$USER/update-boa-api.sh
   ```

### Security Checklist

- [ ] Strong passwords/secret keys in .env
- [ ] Firewall configured properly
- [ ] SSL certificates installed (if using domain)
- [ ] Regular system updates scheduled
- [ ] Log monitoring set up
- [ ] Backup strategy implemented

### Support

If you encounter issues:
1. Check the logs: `docker-compose logs boa-api`
2. Verify environment variables: `cat config/.env`
3. Test network connectivity: `curl localhost:8000/health`
4. Check system resources: `docker stats`