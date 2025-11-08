# Priority Currencies Configuration

## Most Needed Exchange Rates

The following four currencies are configured as **priority currencies** for QuickBooks synchronization:

| Albanian Name | ISO Code | English Name | Usage |
|--------------|----------|--------------|-------|
| Dollar Amerikan | **USD** | US Dollar | Primary foreign currency for international transactions |
| Euro | **EUR** | Euro | European Union transactions |
| Poundi Britanik | **GBP** | British Pound Sterling | UK transactions |
| Franga Zvicerane | **CHF** | Swiss Franc | Swiss transactions |

## How Priority Currencies Work

### 1. In the Scraper

The `BoAScraper` class now includes:

```python
# Priority currencies constant
PRIORITY_CURRENCIES = ['USD', 'EUR', 'GBP', 'CHF']

# Albanian to English name mapping
CURRENCY_NAME_MAPPING = {
    'Dollar Amerikan': 'USD',
    'Euro': 'EUR',
    'Poundi Britanik': 'GBP',
    'Franga Zvicerane': 'CHF',
}
```

### 2. Get Priority Rates Only

Use the new `get_priority_rates()` method:

```python
from src.boa_scraper.scraper import BoAScraper

scraper = BoAScraper()
priority_rates = scraper.get_priority_rates()

# Returns only USD, EUR, GBP, CHF rates
```

### 3. API Endpoint with Filter

Get only priority currencies via API:

```bash
# Get all currencies
curl http://localhost:8000/rates

# Get only priority currencies (USD, EUR, GBP, CHF)
curl http://localhost:8000/rates?priority_only=true
```

### 4. Enhanced Parsing

The scraper now handles both Albanian names and ISO codes:

- **Albanian names** from BoA website are automatically converted to ISO codes
- **Flexible column detection** works with different table layouts
- **Robust parsing** handles various rate formats (comma/dot separators)

## Testing Priority Currencies

### Test on Server

```bash
# SSH into server
ssh root@78.46.201.151

# Test priority currencies endpoint
curl http://localhost:8000/rates?priority_only=true

# Expected output:
{
  "date": "2025-11-08",
  "rates": [
    {
      "currency_code": "USD",
      "currency_name": "Dollar Amerikan (US Dollar)",
      "rate": "100.50",
      "date": "2025-11-08"
    },
    {
      "currency_code": "EUR",
      "currency_name": "Euro",
      "rate": "110.25",
      "date": "2025-11-08"
    },
    {
      "currency_code": "GBP",
      "currency_name": "Poundi Britanik (British Pound)",
      "rate": "125.75",
      "date": "2025-11-08"
    },
    {
      "currency_code": "CHF",
      "currency_name": "Franga Zvicerane (Swiss Franc)",
      "rate": "105.50",
      "date": "2025-11-08"
    }
  ],
  "source": "Bank of Albania",
  "total_rates": 4
}
```

### Sync Only Priority Currencies

To sync only priority currencies to QuickBooks:

```python
from src.boa_scraper.scraper import BoAScraper
from src.quickbooks.sync import QuickBooksSync

# Get priority rates
scraper = BoAScraper()
priority_rates = scraper.get_priority_rates()

# Sync to QuickBooks
qb_sync = QuickBooksSync()
success = qb_sync.sync_rates(priority_rates)
```

## Adding More Priority Currencies

To add more currencies to the priority list, edit `src/boa_scraper/scraper.py`:

```python
# Add more currencies
PRIORITY_CURRENCIES = ['USD', 'EUR', 'GBP', 'CHF', 'CAD', 'JPY']

# Add Albanian name mappings
CURRENCY_NAME_MAPPING = {
    'Dollar Amerikan': 'USD',
    'Euro': 'EUR',
    'Poundi Britanik': 'GBP',
    'Franga Zvicerane': 'CHF',
    'Dollar Kanadez': 'CAD',  # Example: Canadian Dollar
    'Jen Japonez': 'JPY',     # Example: Japanese Yen
}
```

## QuickBooks Integration

When syncing to QuickBooks:

1. **Priority currencies are synced first** (USD, EUR, GBP, CHF)
2. **Currencies are automatically added** to QB active currency list
3. **Exchange rates are posted** with proper format (ALL per 1 foreign unit)
4. **Errors are logged** if any currency fails to sync

### Manual Priority Sync

```bash
# Sync only priority currencies via API
curl -X POST http://localhost:8000/sync \
  -H "Content-Type: application/json" \
  -d '{"priority_only": true}'
```

## Benefits of Priority Currencies

1. **Faster sync times** - Only 4 currencies instead of 20+
2. **Reduced API calls** - Fewer QuickBooks API requests
3. **Focus on essentials** - Most common currencies for business
4. **Better error handling** - Easier to troubleshoot 4 currencies vs many
5. **Lower QB limits** - Stays well within API rate limits

## Currency Rate Format

All rates from BoA are expressed as:

```
Rate = Albanian Lek (ALL) per 1 unit of foreign currency
```

Example:
- USD rate = 100.50 means 1 USD = 100.50 ALL
- EUR rate = 110.25 means 1 EUR = 110.25 ALL

This format matches QuickBooks' expected exchange rate format perfectly.

## Troubleshooting

### Currency Not Found

If a priority currency is missing:

```bash
# Check what the scraper actually found
curl http://localhost:8000/rates

# Check logs for parsing errors
docker-compose logs boa-api | grep -i "currency"
```

### Albanian Name Not Recognized

Add the mapping in `CURRENCY_NAME_MAPPING`:

```python
CURRENCY_NAME_MAPPING = {
    'Dollar Amerikan': 'USD',
    'Your Albanian Name': 'CURRENCY_CODE',
}
```

### Rate Parsing Failed

Check the BoA website structure:
1. Visit https://www.bankofalbania.org
2. Find the exchange rates page
3. Inspect the HTML table structure
4. Update parsing logic in `_parse_exchange_table()` if needed

## Command Reference

```bash
# Get all rates
curl http://localhost:8000/rates

# Get only USD, EUR, GBP, CHF
curl http://localhost:8000/rates?priority_only=true

# Sync all rates to QB
curl -X POST http://localhost:8000/sync

# Check sync status
curl http://localhost:8000/sync/status

# View logs
docker-compose logs -f boa-api

# Test scraper directly
docker-compose exec boa-api python -c "
from src.boa_scraper.scraper import BoAScraper
rates = BoAScraper().get_priority_rates()
print(f'Found {len(rates.rates)} priority rates')
for r in rates.rates:
    print(f'{r.currency_code}: {r.rate}')
"
```
