# Deployment Guide for BoA Exchange Rate API

## Quick Deployment on Hetzner Server

### Prerequisites on Server
- Ubuntu/Debian server
- Docker and Docker Compose installed
- Git installed

### Step 1: Install Dependencies (if not already installed)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install -y docker.io docker-compose git curl

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group (optional, to run without sudo)
sudo usermod -aG docker $USER
```

### Step 2: Clone Repository

```bash
# Clone the repository
git clone <YOUR_REPOSITORY_URL>
cd boa-exchange-rate

# Or if you don't have a repo yet, create the project directory
mkdir -p /opt/boa-exchange-rate
cd /opt/boa-exchange-rate
```

### Step 3: Set Up Environment Variables

```bash
# Create config directory
mkdir -p config

# Create .env file
nano config/.env
```

Add the following to your `.env` file:
```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
LOG_LEVEL=INFO

# QuickBooks Configuration
QB_CLIENT_ID=your_quickbooks_client_id
QB_CLIENT_SECRET=your_quickbooks_client_secret
QB_REDIRECT_URI=https://your-domain.com/auth/callback
QB_ENVIRONMENT=sandbox  # or 'production' for live

# Security
SECRET_KEY=your-secret-key-here

# Database (if using one later)
# DATABASE_URL=postgresql://user:pass@localhost/dbname
```

### Step 4: Deploy with Docker

```bash
# Build and start the application
docker-compose up -d

# Check if containers are running
docker-compose ps

# View logs
docker-compose logs -f boa-api
```

### Step 5: Test the API

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test exchange rates endpoint
curl http://localhost:8000/api/v1/exchange-rates
```

### Step 6: Set Up Nginx (Optional)

If you want to expose the API on port 80/443:

```bash
# The docker-compose.yml already includes nginx configuration
# Just make sure to configure SSL certificates if needed

# For Let's Encrypt SSL:
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### Useful Commands

```bash
# View logs
docker-compose logs boa-api

# Restart services
docker-compose restart

# Update application
git pull
docker-compose down
docker-compose up -d --build

# Stop everything
docker-compose down
```

### Troubleshooting

1. **Port already in use**: Check if port 8000 is free
   ```bash
   sudo netstat -tlnp | grep 8000
   ```

2. **Docker permission denied**: Add user to docker group
   ```bash
   sudo usermod -aG docker $USER
   newgrp docker
   ```

3. **Check container status**:
   ```bash
   docker-compose ps
   docker-compose logs
   ```

### Security Notes

- Change default passwords and secret keys
- Use HTTPS in production
- Keep the system and Docker updated
- Monitor logs regularly

### IPv6 Configuration

Since your server uses IPv6, make sure Docker is configured for IPv6:

```bash
# Check if Docker supports IPv6
docker network ls
```

If you need IPv6 support, edit `/etc/docker/daemon.json`:
```json
{
  "ipv6": true,
  "fixed-cidr-v6": "2001:db8:1::/64"
}
```

Then restart Docker:
```bash
sudo systemctl restart docker
```