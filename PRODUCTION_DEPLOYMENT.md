# 🚀 Production Deployment Guide - Step by Step

## Overview
This guide will help you deploy the BoA Exchange Rate API to production on your Hetzner server.

---

## ✅ PRE-DEPLOYMENT CHECKLIST

### 1. **QuickBooks Setup** (30 minutes)

**A. Create Production App:**
1. Go to https://developer.intuit.com/app/developer/myapps
2. Click "Create an app"
3. Select "QuickBooks Online and Payments"
4. Fill in app details:
   - **App Name**: BoA Exchange Rate Sync
   - **Description**: Exchange rate synchronization for Albanian Lek
   
**B. Configure OAuth:**
1. Go to "Keys & OAuth" tab
2. Add Production Redirect URI:
   - `https://your-domain.com/api/v1/oauth/callback`
3. Copy Production Keys:
   - **Client ID**: Save this
   - **Client Secret**: Save this

**C. Update Scopes:**
Required scopes:
- `com.intuit.quickbooks.accounting` ✅

---

### 2. **Domain & SSL Setup** (20 minutes)

**Option A: Using Existing Domain**
- Point your domain to server IP: `2a01:4f8:c013:3866::/64`
- Update DNS A/AAAA records

**Option B: Using Hetzner Domain**
- Configure in Hetzner Cloud Console
- Server: ubuntu-4gb-fsn1-2

---

### 3. **Update Application Configuration**

**A. Edit `config/.env.production`:**

```bash
# Replace these values:

APP_URL=https://your-actual-domain.com

QB_CLIENT_ID=ABCxxxxxxx123456
QB_CLIENT_SECRET=xxxxxxxxxxxxxxxx
QB_REDIRECT_URI=https://your-actual-domain.com/api/v1/oauth/callback
QB_ENVIRONMENT=production

ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=your_strong_password_here

SECRET_KEY=generate_with_command_below
```

**B. Generate Secure Keys:**

Run this on your local machine:
```powershell
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
```

Copy the output and paste into `.env.production`

---

### 4. **Update Code for Production**

**A. Update `config/settings.py`:**

The app_url will be read from environment variable, so update `.env.production`:
```env
APP_URL=https://your-domain.com
```

**B. Verify Database Path:**
Make sure `data/` directory will be created on server:
```bash
mkdir -p data
```

---

## 📦 DEPLOYMENT STEPS

### **Step 1: Prepare for Upload**

On your local machine:

```powershell
# Create deployment package (excluding unnecessary files)
cd "C:\Users\XheladinPalushi\OneDrive - KONSULENCE.AL\Desktop\BoA exchange rate\boa-exchange-rate-api"

# Create a clean deployment archive
$exclude = @('__pycache__', '*.pyc', 'venv*', '.git', '*.db', 'logs/*')
Compress-Archive -Path * -DestinationPath boa-api-production.zip -Force
```

---

### **Step 2: Access Your Hetzner Server**

**Via Hetzner Console:**
1. Go to https://console.hetzner.cloud/
2. Select your server: **ubuntu-4gb-fsn1-2**
3. Click "Console" button

**Or via SSH (if configured):**
```bash
ssh root@[your-server-ipv6]
```

---

### **Step 3: Server Setup**

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker and dependencies
sudo apt install -y docker.io docker-compose git curl vim

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Create application directory
sudo mkdir -p /opt/boa-exchange-rate
sudo chown $USER:$USER /opt/boa-exchange-rate
cd /opt/boa-exchange-rate
```

---

### **Step 4: Upload Application**

**Option A: Upload via Hetzner Console**
1. Use SFTP client (FileZilla, WinSCP)
2. Connect to server
3. Upload `boa-api-production.zip` to `/opt/boa-exchange-rate/`
4. Extract:
```bash
cd /opt/boa-exchange-rate
unzip boa-api-production.zip
```

**Option B: Git Repository (Recommended)**
```bash
cd /opt/boa-exchange-rate
git clone https://github.com/Xhelo-hub/boa-exchange-rate-api.git .
```

---

### **Step 5: Configure Production Environment**

```bash
# Copy production environment file
cp config/.env.production config/.env

# Edit with your actual values
nano config/.env

# Update these critical values:
# - APP_URL
# - QB_CLIENT_ID
# - QB_CLIENT_SECRET
# - QB_REDIRECT_URI
# - ADMIN_USERNAME
# - ADMIN_PASSWORD
# - SECRET_KEY
# - ENCRYPTION_KEY
```

**Save and exit**: `Ctrl+X`, then `Y`, then `Enter`

---

### **Step 6: Create Required Directories**

```bash
mkdir -p data
mkdir -p logs
mkdir -p static
chmod 755 data logs static
```

---

### **Step 7: Initialize Database**

```bash
# Run database initialization
docker-compose run --rm boa-api python -c "
from src.database.engine import engine, Base
from src.database.models import Admin, Company
Base.metadata.create_all(bind=engine)
print('Database initialized')
"
```

---

### **Step 8: Deploy with Docker**

```bash
# Build and start application
docker-compose up -d --build

# Check if running
docker-compose ps

# View logs
docker-compose logs -f boa-api
```

**Expected output:**
```
boa-api     | INFO:     Started server process [1]
boa-api     | INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

### **Step 9: Configure Firewall**

```bash
# Check firewall status
sudo ufw status

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow API port (if accessing directly)
sudo ufw allow 8000/tcp

# Enable firewall
sudo ufw --force enable
```

---

### **Step 10: Setup SSL Certificate**

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate (replace with your domain)
sudo certbot certonly --standalone -d your-domain.com

# Certificate will be at:
# /etc/letsencrypt/live/your-domain.com/fullchain.pem
# /etc/letsencrypt/live/your-domain.com/privkey.pem
```

---

### **Step 11: Configure Nginx (Optional)**

If using Nginx as reverse proxy:

```bash
# Create Nginx config
sudo nano /etc/nginx/sites-available/boa-api

# Add this configuration:
```

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name your-domain.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/boa-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## ✅ POST-DEPLOYMENT VERIFICATION

### **Test 1: Health Check**

```bash
curl https://your-domain.com/health

# Expected: {"status":"healthy"}
```

### **Test 2: API Documentation**

Visit in browser:
- https://your-domain.com/docs

### **Test 3: Admin Login**

Visit:
- https://your-domain.com/admin

Login with your configured credentials.

### **Test 4: Exchange Rates**

Visit:
- https://your-domain.com/rates

Should display current BoA rates.

### **Test 5: Company Registration**

Visit:
- https://your-domain.com/register

Test the registration flow.

### **Test 6: QuickBooks OAuth**

1. Go to admin dashboard
2. Try connecting a company
3. Verify OAuth flow works

---

## 🔒 SECURITY HARDENING

### 1. **Update Admin Password**

```bash
# In admin dashboard
# Go to Settings → Change Password
```

### 2. **Enable Rate Limiting**

Already configured in application.

### 3. **Setup Backup**

```bash
# Create backup script
nano /root/backup-boa.sh
```

Add:
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/root/backups"
mkdir -p $BACKUP_DIR

# Backup database
cp /opt/boa-exchange-rate/data/boa_exchange_rates.db \
   $BACKUP_DIR/boa_db_$DATE.db

# Backup config
cp /opt/boa-exchange-rate/config/.env \
   $BACKUP_DIR/env_$DATE.bak

# Keep only last 7 days
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
```

```bash
chmod +x /root/backup-boa.sh

# Add to crontab (daily at 2 AM)
crontab -e
0 2 * * * /root/backup-boa.sh
```

### 4. **Monitor Logs**

```bash
# View application logs
docker-compose logs -f boa-api

# Setup log rotation (already configured in Docker)
```

---

## 📊 MONITORING

### **Check Application Status**

```bash
# Container status
docker-compose ps

# Resource usage
docker stats boa-exchange-api

# Recent logs
docker-compose logs --tail=100 boa-api
```

### **Setup Monitoring (Optional)**

```bash
# Install monitoring tools
sudo apt install -y htop iotop
```

---

## 🔄 MAINTENANCE

### **Update Application**

```bash
cd /opt/boa-exchange-rate

# Pull latest code
git pull

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

### **Restart Services**

```bash
# Restart API
docker-compose restart boa-api

# Restart all
docker-compose restart
```

### **View Logs**

```bash
# Real-time logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100
```

---

## 🆘 TROUBLESHOOTING

### **Issue: Container won't start**

```bash
# Check logs
docker-compose logs boa-api

# Check if port is in use
sudo netstat -tlnp | grep 8000

# Restart Docker
sudo systemctl restart docker
```

### **Issue: Can't connect to QuickBooks**

1. Verify QB credentials in `.env`
2. Check redirect URI matches exactly
3. Verify app is published in QB Developer Portal
4. Check logs: `docker-compose logs | grep -i quickbooks`

### **Issue: SSL Certificate Problems**

```bash
# Renew certificate
sudo certbot renew

# Test renewal
sudo certbot renew --dry-run
```

### **Issue: High Memory Usage**

```bash
# Check Docker stats
docker stats

# Restart container
docker-compose restart boa-api
```

---

## 📞 SUPPORT

- **Logs**: `/opt/boa-exchange-rate/logs/`
- **Database**: `/opt/boa-exchange-rate/data/boa_exchange_rates.db`
- **Config**: `/opt/boa-exchange-rate/config/.env`

---

## 🎉 SUCCESS!

Your BoA Exchange Rate API is now live at:
- **API**: https://your-domain.com
- **Admin**: https://your-domain.com/admin
- **Rates**: https://your-domain.com/rates
- **Docs**: https://your-domain.com/docs

**Next Steps:**
1. Test all features
2. Connect first QuickBooks company
3. Monitor for 24 hours
4. Setup automated backups
5. Share registration link with clients
