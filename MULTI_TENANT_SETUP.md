# Multi-Tenant QuickBooks Integration Guide

## Overview

The BoA Exchange Rate API supports **multi-tenant** deployment, allowing multiple companies to install and use the app simultaneously. Each company has its own:

- QuickBooks credentials (OAuth tokens)
- Exchange rate data
- Sync history and logs
- Settings and preferences

## Architecture

### Database Schema

The multi-tenant design uses a `companies` table as the tenant anchor:

```
companies (tenant table)
├── company_id (QuickBooks realm_id)
├── company_name
├── access_token, refresh_token
├── client_id, client_secret
├── home_currency
├── is_active, sync_enabled
└── last_sync_at

exchange_rates (per-company data)
├── company_db_id (FK to companies.id)
├── currency_code, rate, rate_date
├── synced_to_quickbooks
└── UNIQUE(company_db_id, currency_code, rate_date)

scraping_logs (per-company logs)
├── company_db_id (FK to companies.id)
└── scrape results...

quickbooks_syncs (per-company sync audit)
├── company_db_id (FK to companies.id)
└── sync results...
```

### Key Features

1. **Isolated Data**: Each company's data is completely separate
2. **Automatic Token Refresh**: Tokens are refreshed automatically before expiration
3. **Per-Company Sync**: Sync can be triggered for individual companies or all at once
4. **Soft Delete**: Companies can be deactivated without losing historical data
5. **Audit Trail**: Complete history of scrapes and syncs per company

## Installation Flow (Per Company)

### Step 1: Company Initiates Connection

User clicks "Connect to QuickBooks" button in your app, which directs them to:

```
GET /api/v1/oauth/connect
```

This redirects to QuickBooks authorization page.

### Step 2: User Authorizes

User signs in to QuickBooks and selects their company.

### Step 3: OAuth Callback

QuickBooks redirects back to your app:

```
GET /api/v1/oauth/callback?code=xxx&realmId=yyy
```

The API:
1. Exchanges authorization code for access/refresh tokens
2. Creates or updates company record in database
3. Stores encrypted credentials
4. Displays success message to user

### Step 4: Automatic Sync

Once connected, the company is automatically included in daily sync runs.

## API Endpoints

### OAuth Endpoints

#### Connect to QuickBooks
```http
GET /api/v1/oauth/connect
```
Redirects user to QuickBooks authorization page.

#### OAuth Callback
```http
GET /api/v1/oauth/callback?code={auth_code}&realmId={company_id}
```
Handles OAuth callback and stores company credentials.

#### Disconnect Company
```http
GET /api/v1/oauth/disconnect/{company_id}
```
Deactivates a company (soft delete).

#### Get Connection Status
```http
GET /api/v1/oauth/status/{company_id}
```
Returns connection status for a company.

### Company Management Endpoints

#### Sync Single Company
```http
POST /api/v1/companies/{company_id}/sync?target_date=2024-01-15
```
Sync exchange rates for one company.

**Response:**
```json
{
  "success": true,
  "message": "Synced 22 rates for ABC Company",
  "company_id": "9341453199574798",
  "company_name": "ABC Company",
  "date": "2024-01-15",
  "rates_synced": 22
}
```

#### Sync All Companies
```http
POST /api/v1/companies/sync-all?target_date=2024-01-15
```
Sync all active companies at once (for scheduled jobs).

**Response:**
```json
{
  "success": true,
  "message": "Synced 15/16 companies successfully",
  "date": "2024-01-15",
  "total_companies": 16,
  "successful": 15,
  "failed": 1,
  "results": [
    {
      "company_id": "9341453199574798",
      "company_name": "ABC Company",
      "success": true,
      "rates_synced": 22
    }
  ]
}
```

#### Get Company Sync Status
```http
GET /api/v1/companies/{company_id}/sync/status
```
Returns detailed statistics for a company.

**Response:**
```json
{
  "company_id": "9341453199574798",
  "company_name": "ABC Company",
  "is_active": true,
  "sync_enabled": true,
  "created_at": "2024-01-01T10:00:00",
  "last_sync_at": "2024-01-15T08:00:00",
  "exchange_rates": {
    "total": 1540,
    "synced": 1540,
    "pending": 0
  },
  "scraping": {
    "total_attempts": 70,
    "successful": 68,
    "failed": 2
  },
  "syncing": {
    "total_attempts": 68,
    "successful": 68,
    "failed": 0
  }
}
```

#### List All Companies
```http
GET /api/v1/companies/list?active_only=true
```
Returns list of all companies.

**Response:**
```json
{
  "success": true,
  "count": 16,
  "companies": [
    {
      "company_id": "9341453199574798",
      "company_name": "ABC Company",
      "is_active": true,
      "sync_enabled": true,
      "home_currency": "ALL",
      "is_sandbox": false,
      "created_at": "2024-01-01T10:00:00",
      "last_sync_at": "2024-01-15T08:00:00"
    }
  ]
}
```

#### Update Company Settings
```http
PUT /api/v1/companies/{company_id}/settings
Content-Type: application/json

{
  "sync_enabled": true,
  "home_currency": "EUR",
  "company_name": "ABC Company Ltd"
}
```

## Production Deployment

### Environment Variables

```env
# Application
API_HOST=0.0.0.0
API_PORT=8000
ENVIRONMENT=production

# QuickBooks App Credentials (shared across all companies)
QB_CLIENT_ID=your_production_client_id
QB_CLIENT_SECRET=your_production_client_secret
QB_REDIRECT_URI=https://your-domain.com/api/v1/oauth/callback
QB_SANDBOX=False

# Database (PostgreSQL recommended for production)
DATABASE_URL=postgresql://user:password@localhost:5432/boa_exchange_prod

# Security
SECRET_KEY=your_very_secure_secret_key_change_this_in_production

# Scheduler (for daily sync-all job)
SCHEDULE_TIME=08:00
TIMEZONE=Europe/Tirane
```

### Database Migration

Run Alembic migrations to create multi-tenant tables:

```bash
# Create migration
alembic revision --autogenerate -m "Add multi-tenant support"

# Apply migration
alembic upgrade head
```

### Scheduled Sync

Set up a cron job or scheduler to sync all companies daily:

```bash
# crontab -e
0 8 * * * curl -X POST https://your-domain.com/api/v1/companies/sync-all
```

Or use the built-in scheduler in the API.

## Security Considerations

### Token Encryption

**CRITICAL**: In production, encrypt sensitive credentials before storing:

```python
from cryptography.fernet import Fernet

# Generate key once, store in environment
ENCRYPTION_KEY = Fernet.generate_key()

def encrypt_token(token: str) -> str:
    f = Fernet(ENCRYPTION_KEY)
    return f.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    f = Fernet(ENCRYPTION_KEY)
    return f.decrypt(encrypted_token.encode()).decode()
```

Update `Company` model to use encrypted storage:

```python
@property
def access_token(self):
    return decrypt_token(self._access_token)

@access_token.setter
def access_token(self, value):
    self._access_token = encrypt_token(value)
```

### API Authentication

Add authentication to protect company management endpoints:

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials

# Protect endpoints
@router.post("/companies/{company_id}/sync", dependencies=[Depends(verify_api_key)])
async def sync_company_rates(...):
    ...
```

### Rate Limiting

Implement rate limiting to prevent abuse:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/companies/{company_id}/sync")
@limiter.limit("10/minute")
async def sync_company_rates(...):
    ...
```

## Monitoring

### Health Check Endpoint

```http
GET /health
```

Returns status of all companies:

```json
{
  "status": "healthy",
  "total_companies": 16,
  "active_companies": 15,
  "companies_with_expired_tokens": 1,
  "last_sync": "2024-01-15T08:00:00"
}
```

### Logging

All operations are logged with company context:

```
INFO: Company 9341453199574798: Syncing rates for 2024-01-15
INFO: Company 9341453199574798: Successfully synced 22 rates
ERROR: Company 1234567890: Token refresh failed
```

### Alerts

Set up alerts for:
- Token refresh failures
- Sync failures for multiple companies
- Companies not syncing for >24 hours

## Testing Multi-Tenant Setup

### 1. Connect Test Companies

Use QuickBooks Sandbox to create multiple test companies:

```bash
# Connect Company 1
curl http://localhost:8000/api/v1/oauth/connect

# Connect Company 2
curl http://localhost:8000/api/v1/oauth/connect
```

### 2. Test Individual Sync

```bash
curl -X POST http://localhost:8000/api/v1/companies/9341453199574798/sync
```

### 3. Test Batch Sync

```bash
curl -X POST http://localhost:8000/api/v1/companies/sync-all
```

### 4. Verify Data Isolation

```bash
# Get rates for Company 1
curl http://localhost:8000/api/v1/companies/9341453199574798/sync/status

# Get rates for Company 2
curl http://localhost:8000/api/v1/companies/1234567890/sync/status

# Verify they have separate data
```

## Scaling Considerations

### Database Indexing

Ensure proper indexes exist for multi-tenant queries:

```sql
CREATE INDEX idx_company_date ON exchange_rates(company_db_id, rate_date);
CREATE INDEX idx_company_sync_status ON exchange_rates(company_db_id, synced_to_quickbooks);
CREATE INDEX idx_company_active ON companies(is_active, sync_enabled);
```

### Background Jobs

For large numbers of companies, use background job queue:

```python
from celery import Celery

celery = Celery('boa_exchange_rate')

@celery.task
def sync_company_task(company_id: str):
    # Sync company in background
    pass

# Trigger for all companies
for company in companies:
    sync_company_task.delay(company.company_id)
```

### Caching

Cache BoA rates to avoid scraping multiple times per day:

```python
from functools import lru_cache
from datetime import date

@lru_cache(maxsize=7)  # Cache last 7 days
def get_cached_rates(target_date: date):
    return scraper.get_rates_for_date(target_date)
```

## Migration from Single-Tenant

If you have an existing single-tenant deployment:

1. **Add Company Record**: Create initial company for existing credentials
2. **Migrate Data**: Update `exchange_rates` to reference `company_db_id`
3. **Update Routes**: Switch from single-company to company-specific endpoints
4. **Test**: Verify existing company continues to sync correctly
5. **Add New Companies**: Start onboarding additional companies

## Support

For issues or questions about multi-tenant setup:
- Check logs for company-specific errors
- Verify OAuth tokens are valid
- Ensure database indexes exist
- Test token refresh mechanism
- Monitor sync success rates per company
