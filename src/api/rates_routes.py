"""
Public exchange rates routes
Provides access to Bank of Albania exchange rates with search and filtering
"""

from fastapi import APIRouter, Query, HTTPException
from datetime import date, datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel

from ..boa_scraper.scraper import BoAScraper
from ..boa_scraper.models import ExchangeRate
from ..utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/exchange-rates", tags=["exchange-rates"])


class RateResponse(BaseModel):
    """Exchange rate response model"""
    currency_code: str
    currency_name: str
    rate: float
    rate_date: str
    unit: int = 1  # Some currencies like JPY are quoted per 100 units
    
    class Config:
        from_attributes = True


class RatesSearchResponse(BaseModel):
    """Response for rates search"""
    rates: List[RateResponse]
    rate_date: str
    base_currency: str = "ALL"
    total_count: int
    filtered_count: int


@router.get("/current", response_model=RatesSearchResponse)
async def get_current_rates(
    currency: Optional[str] = Query(None, description="Filter by currency code (e.g., USD, EUR)"),
    base_rates_only: bool = Query(False, description="Show only EUR, USD, GBP, CHF"),
):
    """
    Get current exchange rates from Bank of Albania
    
    Query Parameters:
    - currency: Filter by specific currency code (case-insensitive)
    - base_rates_only: If true, only returns EUR, USD, GBP, CHF rates
    """
    try:
        scraper = BoAScraper()
        
        # Get rates based on filter
        if base_rates_only:
            daily_rates = scraper.get_priority_rates()
        else:
            daily_rates = scraper.get_current_rates()
        
        if not daily_rates or not daily_rates.rates:
            raise HTTPException(
                status_code=404,
                detail="No exchange rates available. Please try again later."
            )
        
        # Filter by currency if specified
        filtered_rates = daily_rates.rates
        if currency:
            currency_upper = currency.upper()
            filtered_rates = [
                rate for rate in daily_rates.rates 
                if rate.currency_code.upper() == currency_upper
            ]
            
            if not filtered_rates:
                raise HTTPException(
                    status_code=404,
                    detail=f"Currency {currency.upper()} not found in current rates"
                )
        
        # Convert to response format
        rate_responses = []
        for rate in filtered_rates:
            # Determine unit multiplier (JPY, HUF, RUB are per 100)
            unit = 100 if rate.currency_code in BoAScraper.UNIT_100_CURRENCIES else 1
            
            rate_responses.append(RateResponse(
                currency_code=rate.currency_code,
                currency_name=rate.currency_name,
                rate=float(rate.rate),
                rate_date=rate.rate_date.strftime("%Y-%m-%d"),
                unit=unit
            ))
        
        return RatesSearchResponse(
            rates=rate_responses,
            rate_date=daily_rates.rates_date.strftime("%Y-%m-%d"),
            total_count=len(daily_rates.rates),
            filtered_count=len(rate_responses)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current rates: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch exchange rates: {str(e)}"
        )


@router.get("/search", response_model=RatesSearchResponse)
async def search_rates(
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    currency: Optional[str] = Query(None, description="Filter by currency code"),
    base_rates_only: bool = Query(False, description="Show only EUR, USD, GBP, CHF"),
):
    """
    Search exchange rates by date range and currency
    
    Query Parameters:
    - date_from: Start date in YYYY-MM-DD format
    - date_to: End date in YYYY-MM-DD format (defaults to today)
    - currency: Filter by specific currency code
    - base_rates_only: If true, only returns EUR, USD, GBP, CHF rates
    
    Note: Currently returns most recent rates. Historical data integration pending.
    """
    try:
        # Parse dates if provided
        target_date = None
        if date_from:
            try:
                target_date = datetime.strptime(date_from, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date_from format. Use YYYY-MM-DD"
                )
        
        # For now, we only have current rates
        # In future, this will query historical data
        scraper = BoAScraper()
        
        if target_date and target_date != date.today():
            # Historical rates not yet implemented
            raise HTTPException(
                status_code=501,
                detail="Historical rates search not yet implemented. Showing current rates."
            )
        
        # Get rates
        if base_rates_only:
            daily_rates = scraper.get_priority_rates()
        else:
            daily_rates = scraper.get_current_rates()
        
        if not daily_rates or not daily_rates.rates:
            raise HTTPException(
                status_code=404,
                detail="No exchange rates available"
            )
        
        # Filter by currency
        filtered_rates = daily_rates.rates
        if currency:
            currency_upper = currency.upper()
            filtered_rates = [
                rate for rate in daily_rates.rates 
                if rate.currency_code.upper() == currency_upper
            ]
        
        # Convert to response
        rate_responses = []
        for rate in filtered_rates:
            unit = 100 if rate.currency_code in BoAScraper.UNIT_100_CURRENCIES else 1
            
            rate_responses.append(RateResponse(
                currency_code=rate.currency_code,
                currency_name=rate.currency_name,
                rate=float(rate.rate),
                rate_date=rate.rate_date.strftime("%Y-%m-%d"),
                unit=unit
            ))
        
        return RatesSearchResponse(
            rates=rate_responses,
            rate_date=daily_rates.rates_date.strftime("%Y-%m-%d"),
            total_count=len(daily_rates.rates),
            filtered_count=len(rate_responses)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching rates: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search exchange rates: {str(e)}"
        )


@router.get("/currencies", response_model=List[str])
async def get_available_currencies():
    """
    Get list of all available currency codes
    """
    try:
        scraper = BoAScraper()
        daily_rates = scraper.get_current_rates()
        
        if not daily_rates or not daily_rates.rates:
            return []
        
        # Extract unique currency codes
        currencies = sorted(list(set(rate.currency_code for rate in daily_rates.rates)))
        
        return currencies
        
    except Exception as e:
        logger.error(f"Error getting currencies: {str(e)}")
        return []
