"""
FastAPI routes for the exchange rate API
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import date, datetime

from .schemas import (
    DailyRatesResponse, 
    ExchangeRateResponse,
    SyncRequest,
    SyncResponse,
    SyncStatusResponse,
    HealthResponse,
    ErrorResponse
)
from ..boa_scraper.scraper import BoAScraper
from ..quickbooks.sync import QuickBooksSync
from ..utils.scheduler import trigger_manual_update
from ..utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service="boa-exchange-rate-api",
        version="0.1.0"
    )


@router.get("/rates", response_model=DailyRatesResponse)
async def get_current_rates(priority_only: bool = False):
    """
    Get current exchange rates from Bank of Albania
    
    Args:
        priority_only: If True, return only priority currencies (USD, EUR, GBP, CHF)
    """
    try:
        scraper = BoAScraper()
        
        if priority_only:
            daily_rates = scraper.get_priority_rates()
        else:
            daily_rates = scraper.get_current_rates()
        
        if not daily_rates:
            raise HTTPException(
                status_code=404,
                detail="No exchange rates found"
            )
        
        # Convert to response format
        rate_responses = [
            ExchangeRateResponse(
                currency_code=rate.currency_code,
                currency_name=rate.currency_name,
                rate=rate.rate,
                rate_date=rate.rate_date
            )
            for rate in daily_rates.rates
        ]
        
        return DailyRatesResponse(
            rates_date=daily_rates.rates_date,
            rates=rate_responses,
            source=daily_rates.source,
            total_rates=len(rate_responses)
        )
        
    except Exception as e:
        logger.error(f"Error getting current rates: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving exchange rates: {str(e)}"
        )


@router.get("/rates/{target_date}", response_model=DailyRatesResponse)
async def get_rates_for_date(target_date: date):
    """Get exchange rates for a specific date"""
    try:
        scraper = BoAScraper()
        daily_rates = scraper.get_rates_for_date(target_date)
        
        if not daily_rates:
            raise HTTPException(
                status_code=404,
                detail=f"No exchange rates found for {target_date}"
            )
        
        # Convert to response format
        rate_responses = [
            ExchangeRateResponse(
                currency_code=rate.currency_code,
                currency_name=rate.currency_name,
                rate=rate.rate,
                rate_date=rate.rate_date
            )
            for rate in daily_rates.rates
        ]
        
        return DailyRatesResponse(
            rates_date=daily_rates.rates_date,
            rates=rate_responses,
            source=daily_rates.source,
            total_rates=len(rate_responses)
        )
        
    except Exception as e:
        logger.error(f"Error getting rates for {target_date}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving exchange rates for {target_date}: {str(e)}"
        )


@router.post("/sync", response_model=SyncResponse)
async def trigger_sync(sync_request: SyncRequest = None):
    """Trigger manual synchronization with QuickBooks Online"""
    try:
        if sync_request and sync_request.date_from and sync_request.date_to:
            # Historical sync
            qb_sync = QuickBooksSync()
            result = qb_sync.sync_historical_rates(
                sync_request.date_from,
                sync_request.date_to
            )
            
            if result['success']:
                return SyncResponse(
                    success=True,
                    message=f"Historical sync completed for {sync_request.date_from} to {sync_request.date_to}",
                    synced_rates=result['total_rates']
                )
            else:
                return SyncResponse(
                    success=False,
                    message="Historical sync failed",
                    errors=[result.get('error', 'Unknown error')]
                )
        else:
            # Current day sync
            success = trigger_manual_update()
            
            if success:
                return SyncResponse(
                    success=True,
                    message="Manual sync completed successfully"
                )
            else:
                return SyncResponse(
                    success=False,
                    message="Manual sync failed",
                    errors=["Check logs for details"]
                )
                
    except Exception as e:
        logger.error(f"Error during sync: {str(e)}")
        return SyncResponse(
            success=False,
            message="Sync failed due to error",
            errors=[str(e)]
        )


@router.get("/sync/status", response_model=SyncStatusResponse)
async def get_sync_status():
    """Get QuickBooks synchronization status"""
    try:
        qb_sync = QuickBooksSync()
        status = qb_sync.get_sync_status()
        
        return SyncStatusResponse(**status)
        
    except Exception as e:
        logger.error(f"Error getting sync status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving sync status: {str(e)}"
        )


@router.get("/currencies")
async def get_supported_currencies():
    """Get list of supported currencies"""
    try:
        # This could be enhanced to get actual currencies from BoA or QB
        supported_currencies = [
            {"code": "USD", "name": "US Dollar"},
            {"code": "EUR", "name": "Euro"},
            {"code": "GBP", "name": "British Pound"},
            {"code": "CHF", "name": "Swiss Franc"},
            {"code": "CAD", "name": "Canadian Dollar"},
            {"code": "JPY", "name": "Japanese Yen"},
            {"code": "AUD", "name": "Australian Dollar"},
            {"code": "SEK", "name": "Swedish Krona"},
            {"code": "NOK", "name": "Norwegian Krone"},
            {"code": "DKK", "name": "Danish Krone"},
        ]
        
        return {
            "currencies": supported_currencies,
            "total": len(supported_currencies),
            "base_currency": "ALL"  # Albanian Lek
        }
        
    except Exception as e:
        logger.error(f"Error getting currencies: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving currencies: {str(e)}"
        )


# NOTE: OAuth routes moved to oauth_routes.py for multi-tenant support
# Use /api/v1/oauth/connect and /api/v1/oauth/callback instead

# Temporary redirect for backward compatibility
@router.get("/callback")
async def redirect_old_callback(code: str, realmId: str, state: str = None):
    """Redirect old callback URL to new OAuth callback"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(
        url=f"/api/v1/oauth/callback?code={code}&realmId={realmId}" + (f"&state={state}" if state else ""),
        status_code=307
    )


@router.post("/auth/refresh")
async def refresh_quickbooks_token():
    """Refresh QuickBooks access token"""
    try:
        from ..quickbooks.oauth_client import QuickBooksOAuthClient
        
        oauth_client = QuickBooksOAuthClient()
        
        success = oauth_client.refresh_token()
        
        if success:
            return {
                "message": "Token refreshed successfully",
                "new_access_token": oauth_client.auth_client.access_token[:10] + "..." if oauth_client.auth_client.access_token else None
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to refresh token"
            )
        
    except Exception as e:
        logger.error(f"Error refreshing QuickBooks token: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Token refresh failed: {str(e)}"
        )


@router.get("/auth/user-info")
async def get_quickbooks_user_info(access_token: Optional[str] = Query(None, description="Access token to use")):
    """Get QuickBooks user information"""
    try:
        from ..quickbooks.oauth_client import QuickBooksOAuthClient
        
        oauth_client = QuickBooksOAuthClient()
        
        # Use provided access token or the stored one
        user_info = oauth_client.get_user_info(access_token=access_token)
        
        if user_info:
            return {
                "message": "User info retrieved successfully",
                "user_info": user_info
            }
        else:
            raise HTTPException(
                status_code=404,
                detail="User info not found or access token invalid"
            )
        
    except Exception as e:
        logger.error(f"Error getting QuickBooks user info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get user info: {str(e)}"
        )


@router.get("/auth/company-info")
async def get_quickbooks_company_info():
    """Get QuickBooks company information"""
    try:
        from ..quickbooks.oauth_client import QuickBooksOAuthClient
        
        oauth_client = QuickBooksOAuthClient()
        
        company_info = oauth_client.get_company_info()
        
        if company_info:
            return {
                "message": "Company info retrieved successfully",
                "company_info": company_info
            }
        else:
            raise HTTPException(
                status_code=404,
                detail="Company info not found or not authorized"
            )
        
    except Exception as e:
        logger.error(f"Error getting QuickBooks company info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get company info: {str(e)}"
        )