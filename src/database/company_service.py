"""
Company management service for multi-tenant operations
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from ..database.models import Company
from ..quickbooks.oauth_client import QuickBooksOAuthClient

logger = logging.getLogger(__name__)


class CompanyService:
    """Service for managing company credentials and operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_company_by_id(self, company_id: str) -> Optional[Company]:
        """
        Get company by QuickBooks company ID (realm_id)
        
        Args:
            company_id: QuickBooks realm ID
            
        Returns:
            Company object or None
        """
        return self.db.query(Company).filter(
            Company.company_id == company_id,
            Company.is_active == True
        ).first()
    
    def get_company_by_db_id(self, db_id: int) -> Optional[Company]:
        """
        Get company by database ID
        
        Args:
            db_id: Database primary key
            
        Returns:
            Company object or None
        """
        return self.db.query(Company).filter(Company.id == db_id).first()
    
    def get_all_active_companies(self) -> List[Company]:
        """
        Get all active companies
        
        Returns:
            List of active Company objects
        """
        return self.db.query(Company).filter(
            Company.is_active == True
        ).all()
    
    def get_companies_needing_sync(self) -> List[Company]:
        """
        Get companies that need sync (active and sync_enabled)
        
        Returns:
            List of Company objects ready for sync
        """
        return self.db.query(Company).filter(
            Company.is_active == True,
            Company.sync_enabled == True
        ).all()
    
    def create_or_update_company(
        self,
        company_id: str,
        access_token: str,
        refresh_token: str,
        client_id: str,
        client_secret: str,
        is_sandbox: bool = False,
        company_name: str = None,
        home_currency: str = 'ALL',
        **kwargs
    ) -> Company:
        """
        Create new company or update existing one
        
        Args:
            company_id: QuickBooks realm ID
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            client_id: QB app client ID
            client_secret: QB app client secret
            is_sandbox: Whether using sandbox environment
            company_name: Company display name
            home_currency: Home currency code
            **kwargs: Additional company fields
            
        Returns:
            Company object
        """
        from ..utils.encryption import encrypt_token
        
        try:
            existing = self.get_company_by_id(company_id)
            
            if existing:
                # Update existing company with encrypted tokens
                existing.access_token = encrypt_token(access_token)
                existing.refresh_token = encrypt_token(refresh_token)
                existing.client_id = client_id
                existing.client_secret = encrypt_token(client_secret)
                existing.is_sandbox = is_sandbox
                existing.is_active = True
                existing.updated_at = datetime.utcnow()
                
                if company_name:
                    existing.company_name = company_name
                if home_currency:
                    existing.home_currency = home_currency
                
                # Update additional fields
                for key, value in kwargs.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                
                logger.info(f"Updated company: {company_id}")
                return existing
            else:
                # Create new company with encrypted tokens
                new_company = Company(
                    company_id=company_id,
                    company_name=company_name,
                    access_token=encrypt_token(access_token),
                    refresh_token=encrypt_token(refresh_token),
                    client_id=client_id,
                    client_secret=encrypt_token(client_secret),
                    is_sandbox=is_sandbox,
                    home_currency=home_currency,
                    is_active=True,
                    sync_enabled=True,
                    **kwargs
                )
                
                self.db.add(new_company)
                logger.info(f"Created new company: {company_id}")
                return new_company
                
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Database integrity error: {str(e)}")
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating/updating company: {str(e)}")
            raise
    
    def refresh_company_token(self, company: Company) -> bool:
        """
        Refresh access token for a company
        
        Args:
            company: Company object
            
        Returns:
            True if successful, False otherwise
        """
        from ..utils.encryption import encrypt_token, decrypt_token
        
        try:
            # Decrypt credentials for API call
            oauth_client = QuickBooksOAuthClient(
                client_id=company.client_id,
                client_secret=decrypt_token(company.client_secret),
                redirect_uri="",  # Not needed for token refresh
                environment="sandbox" if company.is_sandbox else "production"
            )
            
            # Refresh the token (decrypt current refresh token)
            token_response = oauth_client.refresh_token(decrypt_token(company.refresh_token))
            
            if not token_response:
                logger.error(f"Failed to refresh token for company {company.company_id}")
                return False
            
            # Update tokens with encryption
            company.access_token = encrypt_token(token_response['access_token'])
            new_refresh = token_response.get('refresh_token', decrypt_token(company.refresh_token))
            company.refresh_token = encrypt_token(new_refresh)
            
            # Calculate new expiration
            expires_in = token_response.get('expires_in', 3600)
            company.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            company.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Refreshed token for company {company.company_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error refreshing token for company {company.company_id}: {str(e)}")
            return False
    
    def check_and_refresh_token_if_needed(self, company: Company) -> bool:
        """
        Check if token needs refresh and refresh if necessary
        
        Args:
            company: Company object
            
        Returns:
            True if token is valid (or was successfully refreshed), False otherwise
        """
        # If no expiration time, assume it needs refresh
        if not company.token_expires_at:
            return self.refresh_company_token(company)
        
        # Refresh if token expires within 5 minutes
        if datetime.utcnow() >= (company.token_expires_at - timedelta(minutes=5)):
            return self.refresh_company_token(company)
        
        return True
    
    def deactivate_company(self, company_id: str, reason: str = None) -> bool:
        """
        Deactivate a company (soft delete)
        
        Args:
            company_id: QuickBooks realm ID
            reason: Optional reason for deactivation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            company = self.get_company_by_id(company_id)
            
            if not company:
                logger.warning(f"Company not found: {company_id}")
                return False
            
            company.is_active = False
            company.sync_enabled = False
            company.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Deactivated company {company_id}: {reason}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deactivating company {company_id}: {str(e)}")
            return False
    
    def update_last_sync(self, company: Company) -> None:
        """
        Update last sync timestamp for a company
        
        Args:
            company: Company object
        """
        try:
            company.last_sync_at = datetime.utcnow()
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating last sync for company {company.company_id}: {str(e)}")
    
    def get_company_stats(self, company_id: str) -> Dict[str, Any]:
        """
        Get statistics for a company
        
        Args:
            company_id: QuickBooks realm ID
            
        Returns:
            Dictionary with company statistics
        """
        try:
            from ..database.models import ExchangeRate, ScrapingLog, QuickBooksSync
            
            company = self.get_company_by_id(company_id)
            
            if not company:
                return {"error": "Company not found"}
            
            # Count exchange rates
            total_rates = self.db.query(ExchangeRate).filter(
                ExchangeRate.company_db_id == company.id
            ).count()
            
            synced_rates = self.db.query(ExchangeRate).filter(
                ExchangeRate.company_db_id == company.id,
                ExchangeRate.synced_to_quickbooks == True
            ).count()
            
            # Count scraping logs
            total_scrapes = self.db.query(ScrapingLog).filter(
                ScrapingLog.company_db_id == company.id
            ).count()
            
            successful_scrapes = self.db.query(ScrapingLog).filter(
                ScrapingLog.company_db_id == company.id,
                ScrapingLog.success == True
            ).count()
            
            # Count sync logs
            total_syncs = self.db.query(QuickBooksSync).filter(
                QuickBooksSync.company_db_id == company.id
            ).count()
            
            successful_syncs = self.db.query(QuickBooksSync).filter(
                QuickBooksSync.company_db_id == company.id,
                QuickBooksSync.sync_status == 'success'
            ).count()
            
            return {
                "company_id": company.company_id,
                "company_name": company.company_name,
                "is_active": company.is_active,
                "sync_enabled": company.sync_enabled,
                "created_at": company.created_at.isoformat(),
                "last_sync_at": company.last_sync_at.isoformat() if company.last_sync_at else None,
                "exchange_rates": {
                    "total": total_rates,
                    "synced": synced_rates,
                    "pending": total_rates - synced_rates
                },
                "scraping": {
                    "total_attempts": total_scrapes,
                    "successful": successful_scrapes,
                    "failed": total_scrapes - successful_scrapes
                },
                "syncing": {
                    "total_attempts": total_syncs,
                    "successful": successful_syncs,
                    "failed": total_syncs - successful_syncs
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting stats for company {company_id}: {str(e)}")
            return {"error": str(e)}
