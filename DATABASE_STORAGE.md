# Database Storage Strategy

## Overview

The BoA Exchange Rate API uses SQLAlchemy ORM with smart incremental update logic to store exchange rates efficiently. The database only stores data when rates actually change, avoiding duplicate entries for weekends and holidays when rates remain static.

## Storage Architecture

### Database Support

**Default: SQLite** (for development and small deployments)
- Location: `data/boa_exchange_rates.db`
- No additional setup required
- Perfect for single-server deployments

**Production: PostgreSQL** (recommended)
```bash
# Connection string format:
DATABASE_URL=postgresql://user:password@localhost:5432/boa_rates
```

**Alternative: MySQL/MariaDB**
```bash
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/boa_rates
```

## Core Tables

### 1. `exchange_rates` - Main Rate Storage

Stores all historical exchange rates with smart update logic:

```sql
CREATE TABLE exchange_rates (
    id INTEGER PRIMARY KEY,
    
    -- Currency Info
    currency_code VARCHAR(10) NOT NULL,        -- USD, EUR, etc.
    currency_name_albanian VARCHAR(100),       -- Dollar Amerikan
    currency_name_english VARCHAR(100),        -- US Dollar
    
    -- Rate Data
    rate_date DATE NOT NULL,                   -- Effective date
    rate NUMERIC(18,6) NOT NULL,               -- Main rate in ALL
    daily_change NUMERIC(18,6),                -- Change from previous day
    
    -- Extended Data (for major currencies)
    buy_rate NUMERIC(18,6),                    -- Bank buying rate
    sell_rate NUMERIC(18,6),                   -- Bank selling rate
    buy_change NUMERIC(18,6),
    sell_change NUMERIC(18,6),
    
    -- Metadata
    unit_multiplier INTEGER DEFAULT 1,         -- 100 for JPY/HUF/RUB
    category VARCHAR(50),                      -- major, regional, precious_metal
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Tracking
    scraped_at TIMESTAMP DEFAULT NOW(),        -- When we fetched it
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Source
    source VARCHAR(100) DEFAULT 'Bank of Albania',
    source_url VARCHAR(500),
    
    -- Prevent duplicates: one rate per currency per date
    UNIQUE(currency_code, rate_date)
);

-- Indexes for fast queries
CREATE INDEX idx_currency_date ON exchange_rates(currency_code, rate_date);
CREATE INDEX idx_date_active ON exchange_rates(rate_date, is_active);
```

**Key Design Decision**: The `UNIQUE(currency_code, rate_date)` constraint prevents duplicate entries. If you try to insert the same currency/date twice, the database will reject it.

### 2. `scraping_logs` - Activity Tracking

Logs every scraping attempt, even when rates don't change:

```sql
CREATE TABLE scraping_logs (
    id INTEGER PRIMARY KEY,
    scraped_at TIMESTAMP DEFAULT NOW(),
    
    -- Results
    success BOOLEAN NOT NULL,
    rates_found INTEGER DEFAULT 0,             -- How many rates scraped
    new_rates_added INTEGER DEFAULT 0,         -- How many were new/changed
    
    -- BoA Metadata
    boa_last_update TIMESTAMP,                 -- From "Përditesimi i fundit"
    
    -- Errors
    error_message VARCHAR(1000)
);
```

**Purpose**: 
- Track scraping frequency (should run daily at 9 AM)
- Identify weekends/holidays when rates don't update
- Debug scraping failures
- Generate health reports

### 3. `currency_metadata` - Static Currency Info

One record per currency with unchanging information:

```sql
CREATE TABLE currency_metadata (
    currency_code VARCHAR(10) PRIMARY KEY,
    currency_name_albanian VARCHAR(100),
    currency_name_english VARCHAR(100),
    
    -- Classification
    category VARCHAR(50),                      -- major, regional, etc.
    is_priority BOOLEAN DEFAULT FALSE,         -- USD, EUR, GBP, CHF
    unit_multiplier INTEGER DEFAULT 1,
    
    -- Tracking
    is_active BOOLEAN DEFAULT TRUE,
    first_seen DATE,
    last_seen DATE,
    
    -- QuickBooks Integration
    sync_to_quickbooks BOOLEAN DEFAULT TRUE,
    last_synced_to_qb TIMESTAMP
);
```

**Purpose**: Avoid storing static data repeatedly in every exchange_rate record.

### 4. `quickbooks_syncs` - Integration Audit Trail

Tracks every QuickBooks synchronization:

```sql
CREATE TABLE quickbooks_syncs (
    id INTEGER PRIMARY KEY,
    
    -- What was synced
    currency_code VARCHAR(10) NOT NULL,
    rate_date DATE NOT NULL,
    rate NUMERIC(18,6) NOT NULL,
    
    -- When and how
    synced_at TIMESTAMP DEFAULT NOW(),
    sync_status VARCHAR(50) NOT NULL,          -- success, failed, pending
    
    -- QuickBooks details
    qb_company_id VARCHAR(100),
    qb_response VARCHAR(2000),
    error_message VARCHAR(1000),
    
    -- Reference
    exchange_rate_id INTEGER
);

CREATE INDEX idx_sync_currency_date ON quickbooks_syncs(currency_code, rate_date);
```

**Purpose**: 
- Compliance/audit trail
- Prevent duplicate syncs
- Track QB integration health

## Smart Update Logic

### How It Works

The `ExchangeRateRepository.save_rates()` method implements intelligent update logic:

```python
def save_rates(self, daily_rates: DailyExchangeRates):
    stats = {'new': 0, 'updated': 0, 'unchanged': 0}
    
    for scraped_rate in daily_rates.rates:
        # Check if rate exists for this currency/date
        existing = db.query(ExchangeRate).filter(
            currency_code == scraped_rate.currency_code,
            rate_date == scraped_rate.date
        ).first()
        
        if existing:
            # Rate exists - check if it changed
            if existing.rate != scraped_rate.rate:
                # ONLY UPDATE IF RATE CHANGED
                existing.rate = scraped_rate.rate
                existing.updated_at = now()
                stats['updated'] += 1
            else:
                # Same rate - do nothing
                stats['unchanged'] += 1
        else:
            # New currency/date - insert it
            new_rate = ExchangeRate(...)
            db.add(new_rate)
            stats['new'] += 1
    
    db.commit()
    return stats
```

### Update Scenarios

**Scenario 1: Friday rates, checked on Saturday**
- Scraper runs Saturday 9 AM
- BoA page still shows Friday's rates (unchanged)
- Database query finds existing rates for Friday
- Rates match → **No database write** (stats['unchanged'] = 22)
- Scraping log created: `success=True, rates_found=22, new_rates_added=0`

**Scenario 2: Monday morning (rates updated)**
- Scraper runs Monday 9 AM
- BoA has new Monday rates
- Database has no records for Monday yet
- **22 new records inserted** (stats['new'] = 22)
- Scraping log: `success=True, rates_found=22, new_rates_added=22`

**Scenario 3: Intraday rate change (rare)**
- Scraper runs Monday 9 AM → inserts Monday rates
- Scraper runs Monday 4 PM → BoA updated rates
- Database has Monday records but rates differ
- **Records updated** (stats['updated'] = X)
- Tracks how many currencies changed

## Scheduling Strategy

### Recommended Schedule

```python
# Run daily at 9:00 AM (after BoA updates at ~12:00 PM Albania time)
schedule.every().day.at("09:00").do(daily_update_task)

# Or run multiple times to catch intraday updates:
schedule.every().day.at("09:00").do(daily_update_task)
schedule.every().day.at("15:00").do(daily_update_task)
```

### Weekend/Holiday Handling

The system automatically handles non-update days:

1. **Scraper runs** every day (including weekends)
2. **BoA page** still shows Friday's rates on Saturday/Sunday
3. **Database** sees existing rates → no insert
4. **Scraping log** records: "checked but no new data"
5. **No wasted storage** for duplicate rates

### Benefits

- **Continuous monitoring**: Know if scraper is working
- **No manual intervention**: System handles weekends automatically
- **Historical accuracy**: Each rate stored once with correct date
- **Disk efficiency**: Only ~30 KB per day of actual updates

## Query Examples

### Get Latest Rates

```python
from database.engine import get_db_manager
from database.repository import ExchangeRateRepository

db_manager = get_db_manager()
with db_manager.get_session() as session:
    repo = ExchangeRateRepository(session)
    
    # Latest rate for each currency
    latest_rates = repo.get_latest_rates()
    
    # Latest for specific currencies
    priority_rates = repo.get_latest_rates(['USD', 'EUR', 'GBP', 'CHF'])
```

### Get Rates for Specific Date

```python
from datetime import date

# Rates for November 22, 2025
rates = repo.get_rates_for_date(date(2025, 11, 22))

# With currency filter
usd_eur = repo.get_rates_for_date(
    date(2025, 11, 22),
    currency_codes=['USD', 'EUR']
)
```

### Historical Rates (Time Series)

```python
from datetime import date, timedelta

# Last 30 days of USD rates
end_date = date.today()
start_date = end_date - timedelta(days=30)

usd_history = repo.get_rate_history(
    currency_code='USD',
    start_date=start_date,
    end_date=end_date
)

# Results ordered newest first
for rate in usd_history:
    print(f"{rate.rate_date}: {rate.rate} ALL (change: {rate.daily_change})")
```

### Scraping Statistics

```python
# Health check: scraping performance last 7 days
stats = repo.get_scraping_stats(days=7)

# Returns:
{
    'period_days': 7,
    'total_attempts': 7,
    'successful_attempts': 7,
    'failed_attempts': 0,
    'success_rate': '100.0%',
    'total_rates_found': 154,  # 22 rates × 7 days
    'total_new_rates': 110,    # 5 weekdays × 22 rates
    'avg_rates_per_scrape': '22.0'
}
```

### Rates Needing QuickBooks Sync

```python
# Get rates that haven't been synced yet
unsynced = repo.get_rates_needing_sync(
    currency_codes=['USD', 'EUR', 'GBP', 'CHF']
)

# Sync them
for rate in unsynced:
    qb_client.create_or_update_exchange_rate(rate)
    repo.mark_synced_to_quickbooks(
        currency_code=rate.currency_code,
        rate_date=rate.rate_date,
        rate=rate.rate,
        status='success'
    )
```

## Data Retention

### Default Strategy: Keep Everything

By default, all historical rates are kept forever. This is practical because:
- Exchange rates compress well (text + numbers)
- Daily storage: ~30 KB (22 currencies × ~1.4 KB per record)
- Yearly storage: ~10 MB
- 10-year storage: ~100 MB

### Optional Cleanup (if needed)

For very long-running systems (5+ years), you can archive old data:

```python
# Archive rates older than 5 years
from datetime import date, timedelta

cutoff_date = date.today() - timedelta(days=5*365)

# Option 1: Export to CSV
old_rates = session.query(ExchangeRate).filter(
    ExchangeRate.rate_date < cutoff_date
).all()

import csv
with open('archive_2020.csv', 'w') as f:
    writer = csv.writer(f)
    # Export...

# Option 2: Move to archive table
session.execute("""
    INSERT INTO exchange_rates_archive 
    SELECT * FROM exchange_rates 
    WHERE rate_date < :cutoff
""", {'cutoff': cutoff_date})

session.execute("""
    DELETE FROM exchange_rates 
    WHERE rate_date < :cutoff
""", {'cutoff': cutoff_date})
```

## Monitoring & Health Checks

### Daily Health Check

Add this to your API:

```python
@router.get("/health/database")
def database_health():
    with db_manager.get_session() as session:
        repo = ExchangeRateRepository(session)
        
        # Check recent scraping
        stats = repo.get_scraping_stats(days=7)
        
        # Check latest data freshness
        latest = repo.get_latest_rates()
        latest_date = max(r.rate_date for r in latest)
        days_old = (date.today() - latest_date).days
        
        return {
            "status": "healthy" if days_old <= 3 else "stale",
            "latest_data_date": latest_date,
            "days_since_update": days_old,
            "scraping_stats": stats,
            "total_currencies": len(latest)
        }
```

### Alerts

Set up alerts for:
- **Stale data**: No new rates in 3+ days (might be long weekend)
- **Scraping failures**: 2+ consecutive failed scrapes
- **Missing currencies**: Expected 22, got less
- **QuickBooks sync failures**: Rates not syncing to QB

## Database Migrations

When you need to modify the schema, use Alembic:

```bash
# Initialize Alembic (first time only)
alembic init alembic

# Create a migration
alembic revision --autogenerate -m "Add sell_rate column"

# Apply migrations
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

## Backup Strategy

### SQLite Backups

```bash
# Simple file copy (while app is stopped)
cp data/boa_exchange_rates.db data/backups/rates_$(date +%Y%m%d).db

# Or use SQLite backup command (while app is running)
sqlite3 data/boa_exchange_rates.db ".backup data/backups/rates_$(date +%Y%m%d).db"
```

### PostgreSQL Backups

```bash
# Daily backup
pg_dump -U postgres boa_rates > backups/boa_rates_$(date +%Y%m%d).sql

# Restore
psql -U postgres boa_rates < backups/boa_rates_20251123.sql
```

### Automated Backup Schedule

```python
# In scheduler.py
schedule.every().day.at("01:00").do(backup_database)

def backup_database():
    import shutil
    from pathlib import Path
    
    db_path = Path('data/boa_exchange_rates.db')
    backup_dir = Path('data/backups')
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = backup_dir / f'rates_{timestamp}.db'
    
    shutil.copy2(db_path, backup_path)
    logger.info(f"Database backed up to {backup_path}")
    
    # Keep only last 30 days
    old_backups = sorted(backup_dir.glob('rates_*.db'))[:-30]
    for old in old_backups:
        old.unlink()
```

## Performance Considerations

### Indexes

The schema includes indexes for common queries:
- `idx_currency_date`: Fast lookups by currency + date
- `idx_date_active`: Fast "all rates for date" queries
- `uix_currency_date`: Enforces uniqueness + fast lookups

### Query Optimization

```python
# GOOD: Get latest rates (uses indexes)
latest = repo.get_latest_rates(['USD', 'EUR'])

# BAD: Load all rates then filter in Python
all_rates = session.query(ExchangeRate).all()
latest = [r for r in all_rates if r.currency_code in ['USD', 'EUR']]
```

### Batch Operations

When syncing historical data:

```python
# GOOD: Batch insert
rates_to_insert = [ExchangeRate(...) for rate in scraped_data]
session.bulk_save_objects(rates_to_insert)
session.commit()

# BAD: Individual inserts in loop
for rate in scraped_data:
    session.add(ExchangeRate(...))
    session.commit()  # Slow!
```

## Summary

**Storage Philosophy**: "Write once, read many"
- Rates stored once per currency per date
- Automatic duplicate prevention via UNIQUE constraint
- Intelligent update logic only writes when rates change
- Weekends/holidays handled automatically (no duplicate storage)
- Scraping logs track activity even when rates don't change
- Efficient for daily updates over years of operation

**Storage Efficiency**: 
- Active day (rates change): ~30 KB
- Weekend/holiday (no change): ~500 bytes (just scraping log)
- Annual storage: ~10 MB
- 10-year projection: ~100 MB

**Reliability**:
- ACID compliance (SQLAlchemy transactions)
- Unique constraints prevent duplicates
- Audit trail for all operations
- Easy backup and restore
