# QuickBooks Multicurrency Integration Guide

## Overview

This API now supports QuickBooks Online multicurrency integration, allowing you to automatically post Bank of Albania exchange rates to QuickBooks.

## How It Works

### 1. Exchange Rate Format

Per QuickBooks multicurrency documentation:
- **Exchange rates** are expressed as: **units of home currency per 1 unit of foreign currency**
- For Albanian Lek (ALL) as home currency: if USD rate = 100, it means 100 ALL = 1 USD
- BoA rates are already in this format, so no conversion is needed

### 2. API Flow

```
BoA Website → Scraper → Exchange Rate Model → QB Sync Service → QuickBooks API
```

**Step-by-step:**
1. **Scrape BoA**: `BoAScraper.get_current_rates()` fetches rates from Bank of Albania website
2. **Parse HTML**: Extracts currency codes, names, and rates from the page table
3. **Create models**: Builds `ExchangeRate` objects (currency_code, rate, date)
4. **Sync to QB**: `QuickBooksSync.sync_rates()` posts each rate to QuickBooks
5. **Add currency**: Ensures currency is in QB active list before posting rate
6. **Post rate**: Uses QB `/exchangerate` endpoint to create/update the rate

### 3. QuickBooks API Endpoints Used

#### Get Exchange Rate
```
GET /company/<realmId>/exchangerate?sourcecurrencycode=<code>&asofdate=<yyyy-mm-dd>
```

#### Create/Update Exchange Rate
```
POST /company/<realmId>/exchangerate
Content-Type: application/json

{
  "SourceCurrencyCode": "USD",
  "TargetCurrencyCode": "ALL",
  "Rate": 100.5,
  "AsOfDate": "2025-11-07",
  "SyncToken": "0"
}
```

#### Get Active Currencies
```
POST /company/<realmId>/query
query=select * from companycurrency
```

#### Add Currency to Active List
```
POST /company/<realmId>/companycurrency
Content-Type: application/json

{
  "Code": "USD"
}
```

## Configuration

### Environment Variables

Add these to your `config/.env` file:

```env
# QuickBooks OAuth Credentials
QB_CLIENT_ID=your_quickbooks_client_id
QB_CLIENT_SECRET=your_quickbooks_client_secret
QB_REDIRECT_URI=https://yourdomain.com/auth/callback

# QuickBooks Environment
QB_ENVIRONMENT=sandbox  # or 'production'
QB_SANDBOX=true

# QuickBooks API Tokens (obtained through OAuth flow)
QB_ACCESS_TOKEN=your_access_token
QB_REFRESH_TOKEN=your_refresh_token
QB_COMPANY_ID=your_realm_id

# Home Currency
HOME_CURRENCY=ALL  # Albanian Lek
```

### Getting QuickBooks Credentials

1. **Create a QB App**: https://developer.intuit.com/
2. **Get Client ID & Secret**: From your app dashboard
3. **Implement OAuth**: Use the OAuth client in `src/quickbooks/oauth_client.py`
4. **Get Tokens**: After user authorizes, you'll receive access & refresh tokens
5. **Get Company ID**: The realm ID from the OAuth redirect

## API Endpoints

### Get Current BoA Rates
```bash
GET /rates
```

Returns current exchange rates from Bank of Albania.

### Sync Rates to QuickBooks
```bash
POST /sync
Content-Type: application/json
```

Triggers manual sync of today's rates to QuickBooks.

### Sync Historical Rates
```bash
POST /sync
Content-Type: application/json

{
  "date_from": "2025-11-01",
  "date_to": "2025-11-07"
}
```

### Check Sync Status
```bash
GET /sync/status
```

## Testing the Integration

### 1. Test on Server (SSH session)

```bash
# Step 1: Get current BoA rates
curl http://localhost:8000/rates

# Step 2: Trigger sync to QuickBooks
curl -X POST http://localhost:8000/sync \
  -H "Content-Type: application/json"

# Step 3: Check sync status
curl http://localhost:8000/sync/status

# Step 4: View logs
docker-compose logs -f boa-api
```

### 2. Test from Local Machine

```bash
# Get rates
curl http://78.46.201.151:8000/rates

# Trigger sync
curl -X POST http://78.46.201.151:8000/sync

# Check status
curl http://78.46.201.151:8000/sync/status
```

### 3. Verify in QuickBooks UI

1. Log into QuickBooks Online
2. Go to **Settings** → **Manage Currency**
3. Check the **Exchange Rate Center**
4. Verify your currencies (USD, EUR, etc.) appear with the latest rates
5. Check the **As Of Date** matches the sync date

## Currency Codes Supported

The API supports all ISO 4217 currency codes that QuickBooks supports. Common ones include:

- **USD** - US Dollar
- **EUR** - Euro
- **GBP** - British Pound
- **CHF** - Swiss Franc
- **CAD** - Canadian Dollar
- **AUD** - Australian Dollar
- **JPY** - Japanese Yen
- **CNY** - Chinese Yuan
- **And 160+ more...**

See full list in the QuickBooks documentation.

## Important Notes

### Multicurrency Prerequisites

1. **Enable Multicurrency**: Must be enabled in QB UI first (cannot be enabled via API)
2. **Set Home Currency**: Define ALL (Albanian Lek) as home currency before first sync
3. **One-time Setup**: Multicurrency cannot be disabled once enabled
4. **Simple Start**: Not available in QuickBooks Simple Start edition

### Rate Behavior

- **Automatic Updates**: QB updates rates automatically, but you can override with API
- **Transaction Lock**: Rates used in transactions cannot be deleted
- **Historical Rates**: Each currency/date combination creates a unique rate record
- **Active Currencies**: Only active currencies can receive rate updates

### Error Handling

The API includes comprehensive error handling:

```python
# Example error response
{
  "success": false,
  "message": "Failed to sync rates",
  "errors": [
    "Currency EUR not found in active currency list",
    "Invalid exchange rate for USD"
  ]
}
```

## Code Structure

### Modified Files

1. **`src/quickbooks/client.py`**
   - Replaced QB library with direct REST API calls
   - Implements QB multicurrency endpoints
   - Handles authentication via Bearer token

2. **`src/quickbooks/sync.py`**
   - Updated to use new client methods
   - Adds currency to active list before posting rate
   - Improved error handling and logging

### Key Methods

#### QuickBooksClient

- `get_existing_exchange_rate()` - Check if rate exists
- `create_or_update_exchange_rate()` - Post rate to QB
- `get_active_currencies()` - List active currencies
- `add_currency()` - Add currency to active list

#### QuickBooksSync

- `sync_rates()` - Sync all rates for a date
- `_sync_single_rate()` - Sync one currency rate
- `sync_historical_rates()` - Sync date range
- `get_sync_status()` - Check connection status

## Troubleshooting

### Common Issues

1. **401 Unauthorized**
   - Token expired → Refresh using OAuth flow
   - Invalid credentials → Check client ID/secret

2. **400 Bad Request**
   - Currency not active → API will auto-add it
   - Invalid rate format → Check decimal conversion
   - Multicurrency not enabled → Enable in QB UI first

3. **404 Not Found**
   - Invalid company ID (realm ID)
   - Currency doesn't exist in QB system

4. **Rate Not Updating**
   - Check SyncToken matches current value
   - Verify date format (YYYY-MM-DD)
   - Ensure rate is positive decimal

### Debug Commands

```bash
# Check QB connection
docker-compose exec boa-api python -c "
from src.quickbooks.sync import QuickBooksSync
sync = QuickBooksSync()
print(sync.get_sync_status())
"

# Test single rate sync
docker-compose exec boa-api python -c "
from src.quickbooks.client import QuickBooksClient
from decimal import Decimal
from datetime import date
client = QuickBooksClient(...)
success = client.create_or_update_exchange_rate('USD', 'ALL', Decimal('100.5'), date.today())
print(f'Success: {success}')
"
```

## Next Steps

1. **Implement OAuth Flow**: Complete the authentication flow for users
2. **Add Token Refresh**: Auto-refresh tokens before expiry
3. **Schedule Sync**: Set up automatic daily sync (cron or scheduler)
4. **Add Webhooks**: Listen for QB events (optional)
5. **Production Deploy**: Move from sandbox to production QB environment

## Resources

- [QuickBooks Multicurrency Docs](https://developer.intuit.com/app/developer/qbo/docs/workflows/manage-multiple-currencies)
- [Exchange Rate API Reference](https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/exchangerate)
- [OAuth 2.0 Guide](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0)
- [Bank of Albania](https://www.bankofalbania.org)
