"""
QuickBooks Online synchronization service
"""

from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal

from .client import QuickBooksClient
from ..boa_scraper.models import DailyExchangeRates, ExchangeRate
from ..config.settings import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


class QuickBooksSync:
    """Service for synchronizing exchange rates with QuickBooks Online"""
    
    def __init__(self):
        """Initialize the sync service"""
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize QuickBooks client with settings"""
        try:
            if not all([
                settings.qb_client_id,
                settings.qb_client_secret,
                settings.qb_access_token,
                settings.qb_refresh_token,
                settings.qb_company_id
            ]):
                logger.warning("QuickBooks credentials not configured")
                return
            
            self.client = QuickBooksClient(
                client_id=settings.qb_client_id,
                client_secret=settings.qb_client_secret,
                access_token=settings.qb_access_token,
                refresh_token=settings.qb_refresh_token,
                company_id=settings.qb_company_id,
                sandbox=settings.qb_sandbox
            )
            
            # Test connection
            if self.client.test_connection():
                logger.info("QuickBooks sync service initialized successfully")
            else:
                logger.error("QuickBooks connection test failed")
                self.client = None
                
        except Exception as e:
            logger.error(f"Failed to initialize QuickBooks sync service: {str(e)}")
            self.client = None
    
    def sync_rates(self, daily_rates: DailyExchangeRates) -> bool:
        """
        Sync exchange rates with QuickBooks Online
        
        Args:
            daily_rates: Daily exchange rates to sync
            
        Returns:
            True if sync was successful, False otherwise
        """
        if not self.client:
            logger.error("QuickBooks client not initialized")
            return False
        
        try:
            logger.info(f"Syncing {len(daily_rates.rates)} exchange rates for {daily_rates.date}")
            
            success_count = 0
            error_count = 0
            
            for rate in daily_rates.rates:
                try:
                    success = self._sync_single_rate(rate)
                    if success:
                        success_count += 1
                    else:
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"Error syncing rate {rate.currency_code}: {str(e)}")
                    error_count += 1
            
            logger.info(f"Sync completed: {success_count} successful, {error_count} errors")
            return error_count == 0
            
        except Exception as e:
            logger.error(f"Error during sync process: {str(e)}")
            return False
    
    def _sync_single_rate(self, rate: ExchangeRate) -> bool:
        """
        Sync a single exchange rate
        
        Args:
            rate: Exchange rate to sync
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if rate already exists for this date and currency
            existing_rates = self.client.get_existing_exchange_rates(rate.date)
            
            existing_rate = None
            for existing in existing_rates:
                if (existing.get('SourceCurrencyCode') == rate.currency_code and
                    existing.get('TargetCurrencyCode') == 'ALL'):  # Albanian Lek
                    existing_rate = existing
                    break
            
            if existing_rate:
                # Update existing rate
                rate_id = existing_rate.get('Id')
                success = self.client.update_exchange_rate(
                    rate_id=rate_id,
                    rate=rate.rate,
                    as_of_date=rate.date
                )
                
                if success:
                    logger.debug(f"Updated existing rate for {rate.currency_code}")
                else:
                    logger.error(f"Failed to update rate for {rate.currency_code}")
                
                return success
            else:
                # Create new rate
                rate_id = self.client.create_exchange_rate(
                    source_currency=rate.currency_code,
                    target_currency='ALL',  # Albanian Lek
                    rate=rate.rate,
                    as_of_date=rate.date
                )
                
                if rate_id:
                    logger.debug(f"Created new rate for {rate.currency_code}")
                    return True
                else:
                    logger.error(f"Failed to create rate for {rate.currency_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error syncing rate for {rate.currency_code}: {str(e)}")
            return False
    
    def sync_historical_rates(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        Sync historical exchange rates for a date range
        
        Args:
            start_date: Start date for sync
            end_date: End date for sync
            
        Returns:
            Dictionary with sync results
        """
        if not self.client:
            logger.error("QuickBooks client not initialized")
            return {'success': False, 'error': 'Client not initialized'}
        
        try:
            from ..boa_scraper.scraper import BoAScraper
            
            scraper = BoAScraper()
            results = {
                'success': True,
                'synced_dates': [],
                'failed_dates': [],
                'total_rates': 0
            }
            
            current_date = start_date
            while current_date <= end_date:
                try:
                    daily_rates = scraper.get_rates_for_date(current_date)
                    
                    if daily_rates:
                        sync_success = self.sync_rates(daily_rates)
                        
                        if sync_success:
                            results['synced_dates'].append(current_date.isoformat())
                            results['total_rates'] += len(daily_rates.rates)
                        else:
                            results['failed_dates'].append(current_date.isoformat())
                    else:
                        logger.warning(f"No rates found for {current_date}")
                        results['failed_dates'].append(current_date.isoformat())
                        
                except Exception as e:
                    logger.error(f"Error syncing rates for {current_date}: {str(e)}")
                    results['failed_dates'].append(current_date.isoformat())
                
                # Move to next day
                current_date = date.fromordinal(current_date.toordinal() + 1)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in historical sync: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_sync_status(self) -> Dict[str, Any]:
        """
        Get synchronization status
        
        Returns:
            Dictionary with sync status information
        """
        status = {
            'client_initialized': self.client is not None,
            'connection_active': False,
            'last_sync': None,  # This would be stored/retrieved from persistence
            'credentials_configured': bool(settings.qb_client_id and 
                                         settings.qb_client_secret and
                                         settings.qb_access_token)
        }
        
        if self.client:
            try:
                status['connection_active'] = self.client.test_connection()
            except Exception as e:
                logger.error(f"Error testing connection: {str(e)}")
                status['connection_active'] = False
        
        return status