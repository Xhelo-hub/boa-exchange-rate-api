"""
Data models for exchange rates
"""

from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal


class ExchangeRate(BaseModel):
    """Exchange rate model"""
    
    currency_code: str = Field(..., description="ISO 4217 currency code (e.g., 'USD', 'EUR')")
    currency_name: str = Field(..., description="Full currency name")
    rate: Decimal = Field(..., description="Exchange rate to Albanian Lek")
    rate_date: date = Field(..., description="Date of the exchange rate")
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            Decimal: str,
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat()
        }


class DailyExchangeRates(BaseModel):
    """Daily exchange rates collection"""
    
    rates_date: date = Field(..., description="Date of the rates")
    rates: List[ExchangeRate] = Field(..., description="List of exchange rates")
    source: str = Field(default="Bank of Albania", description="Source of the rates")
    scraped_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat()
        }