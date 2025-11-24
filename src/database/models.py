"""
SQLAlchemy database models for exchange rate storage
"""

from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, Boolean, Index, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime, date
from decimal import Decimal

Base = declarative_base()


class ExchangeRate(Base):
    """
    Exchange rate model - stores daily rates for each currency
    
    Design for incremental updates:
    - Unique constraint on (currency_code, rate_date) prevents duplicates
    - Only inserts new records when data changes
    - Tracks when data was scraped vs when rate was effective
    """
    __tablename__ = 'exchange_rates'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Currency identification
    currency_code = Column(String(10), nullable=False, index=True)  # USD, EUR, JPY, etc.
    currency_name_albanian = Column(String(100), nullable=False)    # Dollar Amerikan
    currency_name_english = Column(String(100), nullable=True)      # US Dollar
    
    # Rate data
    rate_date = Column(Date, nullable=False, index=True)  # Effective date of the rate
    rate = Column(Numeric(18, 6), nullable=False)         # Main exchange rate (mid-rate)
    daily_change = Column(Numeric(18, 6), nullable=True)  # Change from previous day
    
    # Buy/Sell rates (only for major currencies like USD, EUR)
    buy_rate = Column(Numeric(18, 6), nullable=True)
    sell_rate = Column(Numeric(18, 6), nullable=True)
    buy_change = Column(Numeric(18, 6), nullable=True)
    sell_change = Column(Numeric(18, 6), nullable=True)
    
    # Additional metadata
    unit_multiplier = Column(Integer, default=1)  # 1 for most, 100 for JPY/HUF/RUB
    category = Column(String(50), nullable=True)  # major, regional, precious_metal, etc.
    is_active = Column(Boolean, default=True)     # False for discontinued currencies
    
    # Timestamps
    scraped_at = Column(DateTime, default=func.now(), nullable=False)  # When we fetched it
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Source tracking
    source = Column(String(100), default="Bank of Albania")
    source_url = Column(String(500), nullable=True)
    
    # Indexes for fast queries
    __table_args__ = (
        # Unique constraint: one rate per currency per date
        UniqueConstraint('currency_code', 'rate_date', name='uix_currency_date'),
        # Composite index for common queries
        Index('idx_currency_date', 'currency_code', 'rate_date'),
        Index('idx_date_active', 'rate_date', 'is_active'),
    )
    
    def __repr__(self):
        return f"<ExchangeRate({self.currency_code} = {self.rate} ALL on {self.rate_date})>"


class ScrapingLog(Base):
    """
    Log of scraping attempts - tracks when we checked for updates
    
    Purpose:
    - Track scraping frequency
    - Identify when rates weren't updated (weekends, holidays)
    - Debug scraping issues
    """
    __tablename__ = 'scraping_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    scraped_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    
    # Results
    success = Column(Boolean, nullable=False)
    rates_found = Column(Integer, default=0)        # How many rates were scraped
    new_rates_added = Column(Integer, default=0)    # How many were new/updated
    
    # Metadata from BoA page
    boa_last_update = Column(DateTime, nullable=True)  # "Përditesimi i fundit" timestamp
    
    # Error tracking
    error_message = Column(String(1000), nullable=True)
    
    def __repr__(self):
        return f"<ScrapingLog({self.scraped_at}, found={self.rates_found}, new={self.new_rates_added})>"


class CurrencyMetadata(Base):
    """
    Static metadata about currencies
    
    Purpose:
    - Store currency information that doesn't change daily
    - Track which currencies to monitor
    - Priority/category information for filtering
    """
    __tablename__ = 'currency_metadata'
    
    currency_code = Column(String(10), primary_key=True)
    currency_name_albanian = Column(String(100), nullable=False)
    currency_name_english = Column(String(100), nullable=False)
    
    # Classification
    category = Column(String(50), nullable=True)  # major, regional, precious_metal
    is_priority = Column(Boolean, default=False)  # USD, EUR, GBP, CHF
    unit_multiplier = Column(Integer, default=1)
    
    # Tracking
    is_active = Column(Boolean, default=True)
    first_seen = Column(Date, nullable=True)
    last_seen = Column(Date, nullable=True)
    
    # Sync status
    sync_to_quickbooks = Column(Boolean, default=True)
    last_synced_to_qb = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<CurrencyMetadata({self.currency_code} - {self.currency_name_english})>"


class QuickBooksSync(Base):
    """
    Track QuickBooks synchronization history
    
    Purpose:
    - Know which rates have been sent to QB
    - Prevent duplicate syncs
    - Audit trail for compliance
    """
    __tablename__ = 'quickbooks_syncs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # What was synced
    currency_code = Column(String(10), nullable=False, index=True)
    rate_date = Column(Date, nullable=False, index=True)
    rate = Column(Numeric(18, 6), nullable=False)
    
    # When and how
    synced_at = Column(DateTime, default=func.now(), nullable=False)
    sync_status = Column(String(50), nullable=False)  # success, failed, pending
    
    # QB details
    qb_company_id = Column(String(100), nullable=True)
    qb_response = Column(String(2000), nullable=True)
    error_message = Column(String(1000), nullable=True)
    
    # Reference to source
    exchange_rate_id = Column(Integer, nullable=True)  # FK to exchange_rates.id
    
    __table_args__ = (
        Index('idx_sync_currency_date', 'currency_code', 'rate_date'),
    )
    
    def __repr__(self):
        return f"<QuickBooksSync({self.currency_code} on {self.rate_date}, status={self.sync_status})>"
