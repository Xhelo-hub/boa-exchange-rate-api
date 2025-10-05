"""
Pydantic schemas for API requests and responses
"""

from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal


class ExchangeRateResponse(BaseModel):
    """Exchange rate response schema"""
    
    currency_code: str = Field(..., description="Currency code")
    currency_name: str = Field(..., description="Currency name")
    rate: Decimal = Field(..., description="Exchange rate")
    date: date = Field(..., description="Rate date")
    
    class Config:
        json_encoders = {
            Decimal: str,
            date: lambda v: v.isoformat()
        }


class DailyRatesResponse(BaseModel):
    """Daily exchange rates response schema"""
    
    date: date = Field(..., description="Rates date")
    rates: List[ExchangeRateResponse] = Field(..., description="Exchange rates")
    source: str = Field(..., description="Data source")
    total_rates: int = Field(..., description="Total number of rates")
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat()
        }


class SyncRequest(BaseModel):
    """Sync request schema"""
    
    force_update: bool = Field(default=False, description="Force update existing rates")
    date_from: Optional[date] = Field(None, description="Start date for historical sync")
    date_to: Optional[date] = Field(None, description="End date for historical sync")


class SyncResponse(BaseModel):
    """Sync response schema"""
    
    success: bool = Field(..., description="Sync success status")
    message: str = Field(..., description="Response message")
    synced_rates: int = Field(default=0, description="Number of rates synced")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    sync_date: datetime = Field(default_factory=datetime.now, description="Sync timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SyncStatusResponse(BaseModel):
    """Sync status response schema"""
    
    client_initialized: bool = Field(..., description="QB client initialization status")
    connection_active: bool = Field(..., description="QB connection status")
    credentials_configured: bool = Field(..., description="Credentials configuration status")
    last_sync: Optional[datetime] = Field(None, description="Last sync timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class HealthResponse(BaseModel):
    """Health check response schema"""
    
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorResponse(BaseModel):
    """Error response schema"""
    
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }