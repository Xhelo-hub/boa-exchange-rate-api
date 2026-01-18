"""
SQLAlchemy database models for multi-tenant exchange rate storage
"""

from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, Boolean, Index, UniqueConstraint, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, date
from decimal import Decimal

Base = declarative_base()


class Company(Base):
    """
    Company/Tenant model - stores QuickBooks company credentials
    Each company that installs the app gets an entry here
    """
    __tablename__ = 'companies'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # QuickBooks Company Information
    company_id = Column(String(50), unique=True, nullable=True, index=True)  # realm_id from QB (nullable until connected)
    company_name = Column(String(255), nullable=True)  # QB company name
    
    # OAuth Credentials (should be encrypted in production)
    access_token = Column(Text, nullable=True)  # Nullable until connected
    refresh_token = Column(Text, nullable=True)  # Nullable until connected
    token_expires_at = Column(DateTime, nullable=True)
    
    # Approval Workflow
    approval_status = Column(String(20), default='pending', nullable=False)  # pending, approved, rejected
    approved_by = Column(Integer, ForeignKey('admins.id'), nullable=True)  # Admin who approved
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # App Credentials
    client_id = Column(String(255), nullable=False)
    client_secret = Column(String(255), nullable=False)
    
    # Settings
    is_sandbox = Column(Boolean, default=False)
    home_currency = Column(String(3), default='ALL')  # Home currency code
    is_active = Column(Boolean, default=True)
    sync_enabled = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    last_sync_at = Column(DateTime, nullable=True)
    
    # Contact Information (optional)
    contact_email = Column(String(255), nullable=True)
    contact_name = Column(String(255), nullable=True)
    
    # Business Information
    business_name = Column(String(255), nullable=True)  # Legal business name
    tax_id = Column(String(50), nullable=True)  # NIPT or tax ID
    address = Column(Text, nullable=True)
    phone = Column(String(50), nullable=True)
    
    # Relationships
    sync_settings = relationship("CompanySyncSettings", back_populates="company", uselist=False)
    approver = relationship("Admin", foreign_keys=[approved_by])
    
    # Relationships
    exchange_rates = relationship("ExchangeRate", back_populates="company", cascade="all, delete-orphan")
    scraping_logs = relationship("ScrapingLog", back_populates="company", cascade="all, delete-orphan")
    quickbooks_syncs = relationship("QuickBooksSync", back_populates="company", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Company(id={self.id}, company_id={self.company_id}, name={self.company_name})>"


class ExchangeRate(Base):
    """
    Exchange rate model - stores daily rates for each currency PER COMPANY
    
    Multi-tenant design:
    - Each company has its own set of rates
    - Unique constraint on (company_id, currency_code, rate_date)
    - Tracks which rates have been synced to each company's QuickBooks
    """
    __tablename__ = 'exchange_rates'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Company reference (multi-tenant key)
    company_db_id = Column(Integer, ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    
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
    
    # Sync tracking (per company)
    synced_to_quickbooks = Column(Boolean, default=False)
    synced_at = Column(DateTime, nullable=True)
    
    # Relationships
    company = relationship("Company", back_populates="exchange_rates")
    
    # Indexes for fast queries (multi-tenant)
    __table_args__ = (
        # Unique constraint: one rate per currency per date PER COMPANY
        UniqueConstraint('company_db_id', 'currency_code', 'rate_date', name='uix_company_currency_date'),
        # Composite indexes for common queries
        Index('idx_company_date', 'company_db_id', 'rate_date'),
        Index('idx_company_currency_date', 'company_db_id', 'currency_code', 'rate_date'),
        Index('idx_company_sync_status', 'company_db_id', 'synced_to_quickbooks'),
    )
    
    def __repr__(self):
        return f"<ExchangeRate(company_id={self.company_db_id}, {self.currency_code} = {self.rate} ALL on {self.rate_date})>"


class ScrapingLog(Base):
    """
    Log of scraping attempts - tracks when we checked for updates PER COMPANY
    
    Purpose:
    - Track scraping frequency per company
    - Identify when rates weren't updated (weekends, holidays)
    - Debug scraping issues
    """
    __tablename__ = 'scraping_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Company reference (nullable for global scrapes)
    company_db_id = Column(Integer, ForeignKey('companies.id', ondelete='CASCADE'), nullable=True, index=True)
    
    scraped_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    
    # Results
    success = Column(Boolean, nullable=False)
    rates_found = Column(Integer, default=0)        # How many rates were scraped
    new_rates_added = Column(Integer, default=0)    # How many were new/updated
    
    # Metadata from BoA page
    boa_last_update = Column(DateTime, nullable=True)  # "Përditesimi i fundit" timestamp
    
    # Error tracking
    error_message = Column(String(1000), nullable=True)
    
    # Relationships
    company = relationship("Company", back_populates="scraping_logs")
    
    def __repr__(self):
        return f"<ScrapingLog(company_id={self.company_db_id}, {self.scraped_at}, found={self.rates_found}, new={self.new_rates_added})>"


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
    Track QuickBooks synchronization history PER COMPANY
    
    Purpose:
    - Know which rates have been sent to each company's QB
    - Prevent duplicate syncs per company
    - Audit trail for compliance
    """
    __tablename__ = 'quickbooks_syncs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Company reference
    company_db_id = Column(Integer, ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # What was synced
    currency_code = Column(String(10), nullable=False, index=True)
    rate_date = Column(Date, nullable=False, index=True)
    rate = Column(Numeric(18, 6), nullable=False)
    
    # When and how
    synced_at = Column(DateTime, default=func.now(), nullable=False)
    sync_status = Column(String(50), nullable=False)  # success, failed, pending
    
    # QB details
    qb_response = Column(String(2000), nullable=True)
    error_message = Column(String(1000), nullable=True)
    
    # Reference to source
    exchange_rate_id = Column(Integer, ForeignKey('exchange_rates.id'), nullable=True)
    
    # Relationships
    company = relationship("Company", back_populates="quickbooks_syncs")
    
    __table_args__ = (
        Index('idx_company_sync_date', 'company_db_id', 'rate_date'),
        Index('idx_company_currency_date', 'company_db_id', 'currency_code', 'rate_date'),
    )
    
    def __repr__(self):
        return f"<QuickBooksSync(company_id={self.company_db_id}, {self.currency_code} on {self.rate_date}, status={self.sync_status})>"
