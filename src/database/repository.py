"""
Data access layer for exchange rates
Handles all database operations with smart update logic
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from decimal import Decimal

from .models import ExchangeRate, ScrapingLog, CurrencyMetadata, QuickBooksSync
from ..boa_scraper.models import DailyExchangeRates, ExchangeRate as ScraperExchangeRate
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ExchangeRateRepository:
    """
    Repository for exchange rate database operations
    
    Key features:
    - Upsert logic: only update if rate changed
    - Batch operations for efficiency
    - Query methods for common use cases
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    def save_rates(self, daily_rates: DailyExchangeRates, 
                   boa_timestamp: datetime = None) -> Dict[str, int]:
        """
        Save exchange rates from scraper to database
        
        Smart update logic:
        - Check if rate already exists for this currency/date
        - Only insert/update if rate is different
        - Track which rates are new vs updated
        
        Args:
            daily_rates: Scraped rates from BoA
            boa_timestamp: Timestamp from BoA page
        
        Returns:
            Dict with counts: {'new': X, 'updated': Y, 'unchanged': Z}
        """
        stats = {'new': 0, 'updated': 0, 'unchanged': 0, 'errors': 0}
        
        for scraped_rate in daily_rates.rates:
            try:
                # Check if rate exists
                existing = self.session.query(ExchangeRate).filter(
                    and_(
                        ExchangeRate.currency_code == scraped_rate.currency_code,
                        ExchangeRate.rate_date == scraped_rate.date
                    )
                ).first()
                
                if existing:
                    # Check if rate changed
                    if existing.rate != scraped_rate.rate:
                        # Update existing rate
                        existing.rate = scraped_rate.rate
                        existing.daily_change = scraped_rate.rate - existing.rate
                        existing.scraped_at = datetime.now()
                        existing.updated_at = datetime.now()
                        stats['updated'] += 1
                        logger.debug(f"Updated rate for {scraped_rate.currency_code}")
                    else:
                        stats['unchanged'] += 1
                else:
                    # Insert new rate
                    new_rate = ExchangeRate(
                        currency_code=scraped_rate.currency_code,
                        currency_name_albanian=scraped_rate.currency_name,
                        currency_name_english=self._get_english_name(scraped_rate.currency_code),
                        rate_date=scraped_rate.date,
                        rate=scraped_rate.rate,
                        daily_change=Decimal(0),  # First entry has no change
                        unit_multiplier=self._get_unit_multiplier(scraped_rate.currency_code),
                        category=self._categorize_currency(scraped_rate.currency_code),
                        is_active=True,
                        source="Bank of Albania",
                        source_url="https://www.bankofalbania.org/Tregjet/Kursi_zyrtar_i_kembimit/",
                        scraped_at=datetime.now()
                    )
                    self.session.add(new_rate)
                    stats['new'] += 1
                    logger.debug(f"Added new rate for {scraped_rate.currency_code}")
                
            except Exception as e:
                logger.error(f"Error saving rate for {scraped_rate.currency_code}: {e}")
                stats['errors'] += 1
        
        # Commit all changes
        try:
            self.session.commit()
            
            # Log the scraping attempt
            self._log_scraping_attempt(
                success=True,
                rates_found=len(daily_rates.rates),
                new_rates_added=stats['new'] + stats['updated'],
                boa_timestamp=boa_timestamp
            )
            
            logger.info(
                f"Saved rates: {stats['new']} new, {stats['updated']} updated, "
                f"{stats['unchanged']} unchanged, {stats['errors']} errors"
            )
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to commit rates: {e}")
            raise
        
        return stats
    
    def get_latest_rates(self, currency_codes: List[str] = None) -> List[ExchangeRate]:
        """
        Get the most recent rate for each currency
        
        Args:
            currency_codes: Optional list to filter specific currencies
        
        Returns:
            List of ExchangeRate objects
        """
        # Subquery to get max date per currency
        subquery = self.session.query(
            ExchangeRate.currency_code,
            func.max(ExchangeRate.rate_date).label('max_date')
        ).group_by(ExchangeRate.currency_code)
        
        if currency_codes:
            subquery = subquery.filter(ExchangeRate.currency_code.in_(currency_codes))
        
        subquery = subquery.subquery()
        
        # Join to get full records
        query = self.session.query(ExchangeRate).join(
            subquery,
            and_(
                ExchangeRate.currency_code == subquery.c.currency_code,
                ExchangeRate.rate_date == subquery.c.max_date
            )
        ).filter(ExchangeRate.is_active == True)
        
        return query.all()
    
    def get_rates_for_date(self, target_date: date, 
                          currency_codes: List[str] = None) -> List[ExchangeRate]:
        """
        Get rates for a specific date
        
        Args:
            target_date: Date to query
            currency_codes: Optional list to filter currencies
        
        Returns:
            List of ExchangeRate objects
        """
        query = self.session.query(ExchangeRate).filter(
            and_(
                ExchangeRate.rate_date == target_date,
                ExchangeRate.is_active == True
            )
        )
        
        if currency_codes:
            query = query.filter(ExchangeRate.currency_code.in_(currency_codes))
        
        return query.all()
    
    def get_rate_history(self, currency_code: str, 
                        start_date: date = None,
                        end_date: date = None,
                        limit: int = 30) -> List[ExchangeRate]:
        """
        Get historical rates for a currency
        
        Args:
            currency_code: Currency to query
            start_date: Optional start date
            end_date: Optional end date
            limit: Maximum records to return
        
        Returns:
            List of ExchangeRate objects, newest first
        """
        query = self.session.query(ExchangeRate).filter(
            ExchangeRate.currency_code == currency_code
        )
        
        if start_date:
            query = query.filter(ExchangeRate.rate_date >= start_date)
        if end_date:
            query = query.filter(ExchangeRate.rate_date <= end_date)
        
        query = query.order_by(desc(ExchangeRate.rate_date)).limit(limit)
        
        return query.all()
    
    def get_rates_needing_sync(self, currency_codes: List[str] = None) -> List[ExchangeRate]:
        """
        Get rates that haven't been synced to QuickBooks yet
        
        Args:
            currency_codes: Optional list to filter currencies
        
        Returns:
            List of ExchangeRate objects that need syncing
        """
        # Get latest rates
        latest_rates = self.get_latest_rates(currency_codes)
        
        # Filter out already synced
        unsynced = []
        for rate in latest_rates:
            synced = self.session.query(QuickBooksSync).filter(
                and_(
                    QuickBooksSync.currency_code == rate.currency_code,
                    QuickBooksSync.rate_date == rate.rate_date,
                    QuickBooksSync.sync_status == 'success'
                )
            ).first()
            
            if not synced:
                unsynced.append(rate)
        
        return unsynced
    
    def mark_synced_to_quickbooks(self, currency_code: str, rate_date: date,
                                  rate: Decimal, status: str,
                                  qb_company_id: str = None,
                                  qb_response: str = None,
                                  error_message: str = None):
        """
        Record that a rate was synced to QuickBooks
        
        Args:
            currency_code: Currency that was synced
            rate_date: Date of the rate
            rate: Rate value that was synced
            status: 'success' or 'failed'
            qb_company_id: QB company/realm ID
            qb_response: Response from QB API
            error_message: Error if sync failed
        """
        sync_record = QuickBooksSync(
            currency_code=currency_code,
            rate_date=rate_date,
            rate=rate,
            sync_status=status,
            qb_company_id=qb_company_id,
            qb_response=qb_response,
            error_message=error_message,
            synced_at=datetime.now()
        )
        
        self.session.add(sync_record)
        self.session.commit()
        
        logger.info(f"Recorded QB sync for {currency_code} on {rate_date}: {status}")
    
    def _log_scraping_attempt(self, success: bool, rates_found: int,
                             new_rates_added: int, boa_timestamp: datetime = None,
                             error_message: str = None):
        """Log a scraping attempt"""
        log = ScrapingLog(
            success=success,
            rates_found=rates_found,
            new_rates_added=new_rates_added,
            boa_last_update=boa_timestamp,
            error_message=error_message,
            scraped_at=datetime.now()
        )
        self.session.add(log)
        # Don't commit here - let the caller handle it
    
    def get_scraping_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get scraping statistics for the last N days
        
        Args:
            days: Number of days to look back
        
        Returns:
            Dict with statistics
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        logs = self.session.query(ScrapingLog).filter(
            ScrapingLog.scraped_at >= cutoff_date
        ).all()
        
        total_attempts = len(logs)
        successful = sum(1 for log in logs if log.success)
        total_rates_found = sum(log.rates_found for log in logs)
        total_new_rates = sum(log.new_rates_added for log in logs)
        
        return {
            'period_days': days,
            'total_attempts': total_attempts,
            'successful_attempts': successful,
            'failed_attempts': total_attempts - successful,
            'success_rate': f"{(successful/total_attempts*100):.1f}%" if total_attempts > 0 else "N/A",
            'total_rates_found': total_rates_found,
            'total_new_rates': total_new_rates,
            'avg_rates_per_scrape': f"{(total_rates_found/total_attempts):.1f}" if total_attempts > 0 else "N/A"
        }
    
    def _get_english_name(self, currency_code: str) -> str:
        """Get English name for currency code"""
        names = {
            'USD': 'US Dollar', 'EUR': 'Euro', 'GBP': 'British Pound Sterling',
            'CHF': 'Swiss Franc', 'JPY': 'Japanese Yen', 'AUD': 'Australian Dollar',
            'CAD': 'Canadian Dollar', 'SEK': 'Swedish Krona', 'NOK': 'Norwegian Krone',
            'DKK': 'Danish Krone', 'SDR': 'Special Drawing Rights', 'XAU': 'Gold (Troy Ounce)',
            'XAG': 'Silver (Troy Ounce)', 'CNY': 'Chinese Yuan (Onshore)',
            'CNH': 'Chinese Yuan (Offshore)', 'TRY': 'Turkish Lira', 'BGN': 'Bulgarian Lev',
            'HUF': 'Hungarian Forint', 'RUB': 'Russian Ruble', 'CZK': 'Czech Koruna',
            'MKD': 'Macedonian Denar', 'HRK': 'Croatian Kuna (Obsolete)'
        }
        return names.get(currency_code, currency_code)
    
    def _get_unit_multiplier(self, currency_code: str) -> int:
        """Get unit multiplier (100 for JPY, HUF, RUB, otherwise 1)"""
        return 100 if currency_code in ['JPY', 'HUF', 'RUB'] else 1
    
    def _categorize_currency(self, currency_code: str) -> str:
        """Categorize currency"""
        if currency_code in ['USD', 'EUR', 'GBP', 'CHF']:
            return 'major'
        elif currency_code in ['XAU', 'XAG']:
            return 'precious_metal'
        elif currency_code == 'SDR':
            return 'special_drawing_right'
        elif currency_code in ['BGN', 'HUF', 'RUB', 'CZK', 'MKD', 'HRK']:
            return 'regional'
        else:
            return 'international'
