# Security Configuration Guide

## Overview

The BoA Exchange Rate API includes comprehensive security features:
- **Token Encryption**: All sensitive credentials (access tokens, refresh tokens, client secrets) are encrypted at rest
- **API Key Authentication**: Protected endpoints require authentication
- **Rate Limiting**: Prevents abuse and DoS attacks

## Setup Instructions

### 1. Generate Security Keys

Run these commands to generate secure keys:

```bash
# Generate SECRET_KEY for encryption
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Generate ADMIN_API_KEY for API authentication
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Or use the utility script
python -m src.utils.auth
```

### 2. Add Keys to Environment

Add to your `.env` file:

```env
# Encryption Key (REQUIRED - keep this secret!)
SECRET_KEY=your_generated_secret_key_here

# Admin API Key (REQUIRED for protected endpoints)
ADMIN_API_KEY=your_generated_api_key_here

# Optional: Webhook Secret (for future webhook integrations)
WEBHOOK_SECRET=your_webhook_secret_here
```

**⚠️ CRITICAL**: Never commit these keys to version control!

### 3. Test Encryption

```bash
# Test encryption functionality
python -m src.utils.encryption
```

Output should show successful encryption/decryption.

## Token Encryption

### How It Works

All sensitive tokens are automatically encrypted before storage:

```python
from src.utils.encryption import encrypt_token, decrypt_token

# Encrypt before saving
company.access_token = encrypt_token(raw_token)

# Decrypt when using
decrypted = decrypt_token(company.access_token)
```

### What's Encrypted

- ✅ QuickBooks access tokens
- ✅ QuickBooks refresh tokens
- ✅ QuickBooks client secrets
- ✅ Any future sensitive credentials

### Encryption Algorithm

- **Algorithm**: Fernet (symmetric encryption)
- **Key Derivation**: PBKDF2 with SHA256
- **Iterations**: 100,000
- **Key Length**: 256 bits

## API Authentication

### Protected Endpoints

The following endpoints require the `X-API-Key` header:

#### Company Management
- `POST /api/v1/companies/{company_id}/sync`
- `POST /api/v1/companies/sync-all`
- `GET /api/v1/companies/{company_id}/sync/status`
- `GET /api/v1/companies/list`
- `PUT /api/v1/companies/{company_id}/settings`

#### OAuth Management
- `GET /api/v1/oauth/disconnect/{company_id}`

### Using API Key

#### cURL Example
```bash
curl -X POST https://boa.konsulence.al/api/v1/companies/sync-all \
  -H "X-API-Key: your_admin_api_key_here"
```

#### Python Example
```python
import requests

headers = {
    "X-API-Key": "your_admin_api_key_here"
}

response = requests.post(
    "https://boa.konsulence.al/api/v1/companies/sync-all",
    headers=headers
)
```

#### JavaScript Example
```javascript
fetch('https://boa.konsulence.al/api/v1/companies/sync-all', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your_admin_api_key_here'
  }
})
```

### Public Endpoints

These endpoints do NOT require authentication (needed for OAuth flow):

- `GET /api/v1/oauth/connect` - Initiate QuickBooks connection
- `GET /api/v1/oauth/callback` - OAuth callback handler
- `GET /api/v1/oauth/status/{company_id}` - Connection status

## Rate Limiting

### Default Limits

| Endpoint | Max Requests | Time Window |
|----------|--------------|-------------|
| Individual company sync | 10 | 60 seconds |
| Sync all companies | 5 | 300 seconds (5 min) |
| Status/List endpoints | 20 | 60 seconds |
| Settings update | 10 | 60 seconds |

### Rate Limit Response

When rate limit is exceeded:

```json
{
  "detail": "Rate limit exceeded. Please try again later."
}
```

HTTP Status: `429 Too Many Requests`
Header: `Retry-After: 60`

### Custom Rate Limits

Modify limits in endpoint decorators:

```python
await check_rate_limit(
    client_ip,
    max_requests=100,  # Increase limit
    window_seconds=3600  # 1 hour window
)
```

## Production Security Checklist

### Before Deployment

- [ ] Generate strong `SECRET_KEY` (min 32 characters)
- [ ] Generate strong `ADMIN_API_KEY` (min 32 characters)
- [ ] Add keys to production `.env` file
- [ ] **Never** commit `.env` to git
- [ ] Enable HTTPS/SSL for production domain
- [ ] Configure firewall rules
- [ ] Set up secure backup for encryption keys

### Database Security

- [ ] Use PostgreSQL with SSL/TLS in production
- [ ] Set strong database password
- [ ] Restrict database access to application server only
- [ ] Enable automatic backups
- [ ] Encrypt database backups

### Key Storage Best Practices

#### Option 1: Environment Variables (Simple)
```bash
export SECRET_KEY="your_key_here"
export ADMIN_API_KEY="your_key_here"
```

#### Option 2: Secrets Management (Recommended for Production)

**AWS Secrets Manager:**
```python
import boto3
import json

def get_secret():
    client = boto3.client('secretsmanager', region_name='eu-central-1')
    response = client.get_secret_value(SecretId='boa-exchange-rate-secrets')
    return json.loads(response['SecretString'])

secrets = get_secret()
SECRET_KEY = secrets['SECRET_KEY']
ADMIN_API_KEY = secrets['ADMIN_API_KEY']
```

**HashiCorp Vault:**
```python
import hvac

client = hvac.Client(url='https://vault.yourcompany.com')
secret = client.secrets.kv.v2.read_secret_version(path='boa-exchange-rate')
SECRET_KEY = secret['data']['data']['SECRET_KEY']
```

#### Option 3: Docker Secrets
```yaml
# docker-compose.yml
services:
  api:
    secrets:
      - secret_key
      - admin_api_key

secrets:
  secret_key:
    external: true
  admin_api_key:
    external: true
```

### Key Rotation

Rotate encryption keys periodically:

1. **Generate New Key:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

2. **Re-encrypt Data:**
```python
from src.utils.encryption import EncryptionManager

old_manager = EncryptionManager(old_key)
new_manager = EncryptionManager(new_key)

for company in companies:
    # Decrypt with old key
    access_token = old_manager.decrypt(company.access_token)
    refresh_token = old_manager.decrypt(company.refresh_token)
    
    # Re-encrypt with new key
    company.access_token = new_manager.encrypt(access_token)
    company.refresh_token = new_manager.encrypt(refresh_token)
    
db.commit()
```

3. **Update Environment Variable**

## Monitoring and Logging

### Security Events to Monitor

```python
# Failed authentication attempts
logger.warning(f"Invalid API key attempt from {client_ip}")

# Rate limit exceeded
logger.warning(f"Rate limit exceeded for {client_ip}")

# Encryption failures
logger.error(f"Encryption failed: {error}")

# Token refresh failures
logger.error(f"Token refresh failed for company {company_id}")
```

### Recommended Alerts

- Multiple failed authentication attempts from same IP
- Rate limit exceeded repeatedly
- Encryption/decryption errors
- Database connection errors
- QuickBooks API errors

## Troubleshooting

### "SECRET_KEY must be provided"

**Cause**: Missing SECRET_KEY in environment

**Fix**:
```bash
export SECRET_KEY="your_generated_key"
# Or add to .env file
```

### "Invalid API key"

**Cause**: Wrong or missing X-API-Key header

**Fix**: Include correct API key in request:
```bash
curl -H "X-API-Key: your_key_here" https://...
```

### "Decryption failed"

**Cause**: SECRET_KEY changed or data corrupted

**Fix**: 
- Verify SECRET_KEY matches the one used for encryption
- Check database integrity
- Re-establish OAuth connections if needed

### Rate Limit Exceeded

**Cause**: Too many requests in time window

**Fix**: Wait for time window to expire or implement exponential backoff:

```python
import time

def sync_with_retry(company_id, max_retries=3):
    for attempt in range(max_retries):
        try:
            return sync_company(company_id)
        except RateLimitError:
            wait_time = 2 ** attempt  # Exponential backoff
            time.sleep(wait_time)
    
    raise Exception("Max retries exceeded")
```

## Security Audit

### Regular Security Checks

1. **Review Access Logs**
```bash
grep "Invalid API key" logs/api.log | wc -l
grep "Rate limit exceeded" logs/api.log
```

2. **Check Token Expiration**
```sql
SELECT company_id, token_expires_at 
FROM companies 
WHERE token_expires_at < NOW();
```

3. **Verify Encryption**
```python
# All tokens should be encrypted (not readable as plain text)
SELECT access_token FROM companies LIMIT 1;
-- Should see encrypted gibberish, not "eyJ..." JWT format
```

4. **Monitor Failed Syncs**
```sql
SELECT company_id, COUNT(*) 
FROM quickbooks_syncs 
WHERE sync_status = 'failed' 
GROUP BY company_id 
HAVING COUNT(*) > 5;
```

## Support

For security issues:
- **Do NOT** post security vulnerabilities in public issues
- Email: [your-security-email@domain.com]
- Encrypt sensitive information with PGP when reporting vulnerabilities
