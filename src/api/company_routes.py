"""
Multi-tenant sync routes for QuickBooks integration
Handles sync operations for multiple companies
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, datetime
import logging

from ..database.engine import get_db
from ..database.models import Company
from ..database.company_service import CompanyService
from ..quickbooks.sync import QuickBooksSync
from ..boa_scraper.scraper import BoAScraper
from ..utils.auth import verify_admin_key, check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/companies", tags=["multi-tenant-sync"])


@router.post("/{company_id}/sync", dependencies=[Depends(verify_admin_key)])
async def sync_company_rates(
    company_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    target_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Sync exchange rates for a specific company
    
    **Requires Authentication:** X-API-Key header
    
    Path Parameters:
        company_id: QuickBooks company ID (realm_id)
        
    Query Parameters:
        target_date: Date to sync (YYYY-MM-DD), defaults to today
        
    Returns: Sync status and results
    """
    # Rate limiting
    client_ip = request.client.host
    await check_rate_limit(client_ip, max_requests=10, window_seconds=60)
    try:
        company_service = CompanyService(db)
        company = company_service.get_company_by_id(company_id)
        
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        if not company.is_active:
            raise HTTPException(status_code=400, detail="Company is not active")
        
        if not company.sync_enabled:
            raise HTTPException(status_code=400, detail="Sync is disabled for this company")
        
        # Check and refresh token if needed
        if not company_service.check_and_refresh_token_if_needed(company):
            raise HTTPException(status_code=401, detail="Failed to refresh access token")
        
        # Parse target date
        if target_date:
            try:
                sync_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        else:
            sync_date = date.today()
        
        # Scrape rates from BoA
        scraper = BoAScraper()
        daily_rates = scraper.get_rates_for_date(sync_date)
        
        if not daily_rates:
            return {
                "success": False,
                "message": "No rates available for the specified date",
                "company_id": company_id,
                "date": sync_date.isoformat()
            }
        
        # Import decrypt function here to avoid early initialization
        from ..utils.encryption import decrypt_token
        
        # Initialize sync service for this company (decrypt credentials)
        sync_service = QuickBooksSync(
            client_id=company.client_id,
            client_secret=decrypt_token(company.client_secret),
            access_token=decrypt_token(company.access_token),
            refresh_token=decrypt_token(company.refresh_token),
            company_id=company.company_id,
            sandbox=company.is_sandbox
        )
        
        # Perform sync
        success = sync_service.sync_rates(daily_rates, company_db_id=company.id, db=db)
        
        # Update last sync timestamp
        if success:
            company_service.update_last_sync(company)
        
        return {
            "success": success,
            "message": f"Synced {len(daily_rates.rates)} rates for {company.company_name or company_id}",
            "company_id": company_id,
            "company_name": company.company_name,
            "date": sync_date.isoformat(),
            "rates_synced": len(daily_rates.rates)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing rates for company {company_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/sync-all", dependencies=[Depends(verify_admin_key)])
async def sync_all_companies(
    request: Request,
    background_tasks: BackgroundTasks,
    target_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Sync exchange rates for ALL active companies
    
    **Requires Authentication:** X-API-Key header
    
    Useful for scheduled batch operations
    
    Query Parameters:
        target_date: Date to sync (YYYY-MM-DD), defaults to today
        
    Returns: Sync results for all companies
    """
    # Rate limiting
    client_ip = request.client.host
    await check_rate_limit(client_ip, max_requests=5, window_seconds=300)
    try:
        company_service = CompanyService(db)
        companies = company_service.get_companies_needing_sync()
        
        if not companies:
            return {
                "success": True,
                "message": "No active companies found",
                "companies_synced": 0,
                "results": []
            }
        
        # Parse target date
        if target_date:
            try:
                sync_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        else:
            sync_date = date.today()
        
        # Scrape rates once (shared across all companies)
        scraper = BoAScraper()
        daily_rates = scraper.get_rates_for_date(sync_date)
        
        if not daily_rates:
            return {
                "success": False,
                "message": "No rates available for the specified date",
                "date": sync_date.isoformat(),
                "companies_synced": 0
            }
        
        results = []
        success_count = 0
        error_count = 0
        
        for company in companies:
            try:
                # Check and refresh token
                if not company_service.check_and_refresh_token_if_needed(company):
                    logger.error(f"Failed to refresh token for company {company.company_id}")
                    results.append({
                        "company_id": company.company_id,
                        "success": False,
                        "error": "Token refresh failed"
                    })
                    error_count += 1
                    continue
                
                # Initialize sync service for this company
                # Decrypt credentials for this company
                sync_service = QuickBooksSync(
                    client_id=company.client_id,
                    client_secret=decrypt_token(company.client_secret),
                    access_token=decrypt_token(company.access_token),
                    refresh_token=decrypt_token(company.refresh_token),
                    company_id=company.company_id,
                    sandbox=company.is_sandbox
                )
                
                # Perform sync
                success = sync_service.sync_rates(daily_rates, company_db_id=company.id, db=db)
                
                if success:
                    company_service.update_last_sync(company)
                    success_count += 1
                    results.append({
                        "company_id": company.company_id,
                        "company_name": company.company_name,
                        "success": True,
                        "rates_synced": len(daily_rates.rates)
                    })
                else:
                    error_count += 1
                    results.append({
                        "company_id": company.company_id,
                        "success": False,
                        "error": "Sync failed"
                    })
                    
            except Exception as e:
                logger.error(f"Error syncing company {company.company_id}: {str(e)}")
                error_count += 1
                results.append({
                    "company_id": company.company_id,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "success": error_count == 0,
            "message": f"Synced {success_count}/{len(companies)} companies successfully",
            "date": sync_date.isoformat(),
            "total_companies": len(companies),
            "successful": success_count,
            "failed": error_count,
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch sync: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch sync failed: {str(e)}")


@router.get("/{company_id}/sync/status", dependencies=[Depends(verify_admin_key)])
async def get_company_sync_status(
    company_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get sync status for a specific company
    
    **Requires Authentication:** X-API-Key header
    
    Path Parameters:
        company_id: QuickBooks company ID (realm_id)
        
    Returns: Sync status information
    """
    # Rate limiting
    client_ip = request.client.host
    await check_rate_limit(client_ip, max_requests=20, window_seconds=60)
    try:
        company_service = CompanyService(db)
        stats = company_service.get_company_stats(company_id)
        
        if "error" in stats:
            raise HTTPException(status_code=404, detail=stats["error"])
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sync status for company {company_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get sync status")


@router.get("/list", dependencies=[Depends(verify_admin_key)])
async def list_all_companies(
    request: Request,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    List all companies in the system
    
    **Requires Authentication:** X-API-Key header
    
    Query Parameters:
        active_only: Only return active companies (default: true)
        
    Returns: List of companies
    """
    # Rate limiting
    client_ip = request.client.host
    await check_rate_limit(client_ip, max_requests=20, window_seconds=60)
    try:
        company_service = CompanyService(db)
        
        if active_only:
            companies = company_service.get_all_active_companies()
        else:
            companies = db.query(Company).all()
        
        return {
            "success": True,
            "count": len(companies),
            "companies": [
                {
                    "company_id": c.company_id,
                    "company_name": c.company_name,
                    "is_active": c.is_active,
                    "sync_enabled": c.sync_enabled,
                    "home_currency": c.home_currency,
                    "is_sandbox": c.is_sandbox,
                    "created_at": c.created_at.isoformat(),
                    "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None
                }
                for c in companies
            ]
        }
        
    except Exception as e:
        logger.error(f"Error listing companies: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list companies")


@router.put("/{company_id}/settings", dependencies=[Depends(verify_admin_key)])
async def update_company_settings(
    company_id: str,
    request: Request,
    sync_enabled: Optional[bool] = None,
    home_currency: Optional[str] = None,
    company_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Update company settings
    
    **Requires Authentication:** X-API-Key header
    
    Path Parameters:
        company_id: QuickBooks company ID (realm_id)
        
    Body Parameters:
        sync_enabled: Enable/disable automatic sync
        home_currency: Home currency code
        company_name: Company display name
        
    Returns: Updated company information
    """
    # Rate limiting
    client_ip = request.client.host
    await check_rate_limit(client_ip, max_requests=10, window_seconds=60)
    try:
        company_service = CompanyService(db)
        company = company_service.get_company_by_id(company_id)
        
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Update settings
        if sync_enabled is not None:
            company.sync_enabled = sync_enabled
        
        if home_currency is not None:
            company.home_currency = home_currency
        
        if company_name is not None:
            company.company_name = company_name
        
        company.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            "success": True,
            "message": "Company settings updated",
            "company": {
                "company_id": company.company_id,
                "company_name": company.company_name,
                "sync_enabled": company.sync_enabled,
                "home_currency": company.home_currency,
                "updated_at": company.updated_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating company settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update settings")
