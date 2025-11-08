"""
Bank of Albania exchange rate scraper
"""

import requests
from bs4 import BeautifulSoup
from datetime import date, datetime
from typing import List, Optional, Dict
from decimal import Decimal
import re

from .models import ExchangeRate, DailyExchangeRates
from ..utils.logger import get_logger

logger = get_logger(__name__)


class BoAScraper:
    """Bank of Albania exchange rate scraper"""
    
    # Priority currencies - most needed for QuickBooks sync
    PRIORITY_CURRENCIES = ['USD', 'EUR', 'GBP', 'CHF']
    
    # Albanian to English currency name mapping
    CURRENCY_NAME_MAPPING = {
        'Dollar Amerikan': 'USD',
        'Euro': 'EUR',
        'Poundi Britanik': 'GBP',
        'Franga Zvicerane': 'CHF',
    }
    
    def __init__(self, base_url: str = "https://www.bankofalbania.org"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_current_rates(self) -> Optional[DailyExchangeRates]:
        """
        Get current exchange rates from Bank of Albania
        
        Returns:
            DailyExchangeRates object or None if scraping fails
        """
        try:
            # The actual URL pattern for BoA exchange rates
            # This is a placeholder - you'll need to inspect the actual BoA website
            url = f"{self.base_url}/web/Kursi_i_kembimit_te_lekut_2024_4411_1.php"
            
            logger.info(f"Scraping exchange rates from: {url}")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Parse the exchange rates table
            rates = self._parse_exchange_table(soup)
            
            if rates:
                daily_rates = DailyExchangeRates(
                    date=date.today(),
                    rates=rates
                )
                logger.info(f"Successfully scraped {len(rates)} exchange rates")
                return daily_rates
            else:
                logger.warning("No exchange rates found on the page")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Request error while scraping BoA: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error scraping BoA exchange rates: {str(e)}")
            return None
    
    def get_rates_for_date(self, target_date: date) -> Optional[DailyExchangeRates]:
        """
        Get exchange rates for a specific date
        
        Args:
            target_date: Date to get rates for
            
        Returns:
            DailyExchangeRates object or None if not found
        """
        # This would require finding the URL pattern for historical rates
        # For now, return current rates if target_date is today
        if target_date == date.today():
            return self.get_current_rates()
        
        logger.warning(f"Historical rates for {target_date} not implemented yet")
        return None
    
    def _parse_exchange_table(self, soup: BeautifulSoup) -> List[ExchangeRate]:
        """
        Parse the exchange rates table from the HTML
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            List of ExchangeRate objects
        """
        rates = []
        
        try:
            # Find the exchange rates table
            # This selector will need to be updated based on actual BoA website structure
            table = soup.find('table', class_='table')  # Placeholder selector
            
            if not table:
                # Try alternative selectors
                table = soup.find('table')
                
            if table:
                rows = table.find_all('tr')[1:]  # Skip header row
                
                for row in rows:
                    cols = row.find_all(['td', 'th'])
                    
                    if len(cols) >= 2:  # At minimum: Currency name and Rate
                        try:
                            # Try to extract currency info from different column layouts
                            # Layout 1: Name | Code | Rate
                            # Layout 2: Name | Rate
                            # Layout 3: Code | Rate
                            
                            col0_text = cols[0].get_text(strip=True)
                            col1_text = cols[1].get_text(strip=True) if len(cols) > 1 else ""
                            col2_text = cols[2].get_text(strip=True) if len(cols) > 2 else ""
                            
                            # Determine which column has the rate (look for numbers)
                            rate_text = None
                            currency_name_raw = None
                            currency_code = None
                            
                            if re.search(r'\d+[.,]\d+', col2_text):
                                # Layout 1: Name | Code | Rate
                                currency_name_raw = col0_text
                                currency_code = col1_text
                                rate_text = col2_text
                            elif re.search(r'\d+[.,]\d+', col1_text):
                                # Layout 2 or 3: Name/Code | Rate
                                currency_name_raw = col0_text
                                rate_text = col1_text
                            
                            if not rate_text:
                                continue
                            
                            # Clean and parse the rate
                            rate_text = re.sub(r'[^\d.,]', '', rate_text)
                            rate_text = rate_text.replace(',', '.')
                            
                            if not rate_text:
                                continue
                            
                            # Normalize currency code from Albanian name
                            if not currency_code or len(currency_code) != 3:
                                currency_code = self._normalize_currency_name(currency_name_raw)
                            
                            # If we have a valid code and rate, create the exchange rate
                            if currency_code and rate_text:
                                rate = Decimal(rate_text)
                                
                                # Use the full name mapping
                                currency_name = self._get_currency_name(currency_code)
                                
                                exchange_rate = ExchangeRate(
                                    currency_code=currency_code,
                                    currency_name=currency_name,
                                    rate=rate,
                                    date=date.today()
                                )
                                
                                rates.append(exchange_rate)
                                logger.debug(f"Parsed rate: {currency_code} = {rate}")
                                
                        except (ValueError, IndexError, Exception) as e:
                            logger.warning(f"Error parsing rate row: {str(e)}")
                            continue
            
            # If no table found, try to find rates in a different format
            if not rates:
                rates = self._parse_alternative_format(soup)
                
        except Exception as e:
            logger.error(f"Error parsing exchange table: {str(e)}")
        
        return rates
    
    def _parse_alternative_format(self, soup: BeautifulSoup) -> List[ExchangeRate]:
        """
        Parse exchange rates from alternative HTML format
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            List of ExchangeRate objects
        """
        rates = []
        
        # Add alternative parsing logic here
        # This might include parsing from div elements, lists, etc.
        
        # Example: look for currency codes and rates in text
        text_content = soup.get_text()
        
        # Common currency patterns
        currency_patterns = {
            'USD': r'USD.*?(\d+[.,]\d+)',
            'EUR': r'EUR.*?(\d+[.,]\d+)',
            'GBP': r'GBP.*?(\d+[.,]\d+)',
            'CHF': r'CHF.*?(\d+[.,]\d+)',
            'CAD': r'CAD.*?(\d+[.,]\d+)',
            'JPY': r'JPY.*?(\d+[.,]\d+)',
        }
        
        for currency_code, pattern in currency_patterns.items():
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                try:
                    rate_text = match.group(1).replace(',', '.')
                    rate = Decimal(rate_text)
                    
                    exchange_rate = ExchangeRate(
                        currency_code=currency_code,
                        currency_name=self._get_currency_name(currency_code),
                        rate=rate,
                        date=date.today()
                    )
                    
                    rates.append(exchange_rate)
                    
                except ValueError:
                    continue
        
        return rates
    
    def _normalize_currency_name(self, raw_name: str) -> str:
        """
        Convert Albanian currency name to ISO code
        
        Args:
            raw_name: Currency name from BoA website (e.g., 'Dollar Amerikan')
            
        Returns:
            ISO 4217 currency code (e.g., 'USD')
        """
        # Try exact match first
        if raw_name in self.CURRENCY_NAME_MAPPING:
            return self.CURRENCY_NAME_MAPPING[raw_name]
        
        # Try case-insensitive partial match
        raw_lower = raw_name.lower().strip()
        for alb_name, code in self.CURRENCY_NAME_MAPPING.items():
            if alb_name.lower() in raw_lower or raw_lower in alb_name.lower():
                return code
        
        # If already a code (USD, EUR, etc.), return as-is
        if len(raw_name) == 3 and raw_name.isupper():
            return raw_name
        
        return raw_name
    
    def _get_currency_name(self, currency_code: str) -> str:
        """
        Get full currency name from currency code
        
        Args:
            currency_code: ISO 4217 currency code
            
        Returns:
            Full currency name
        """
        currency_names = {
            'USD': 'Dollar Amerikan (US Dollar)',
            'EUR': 'Euro',
            'GBP': 'Poundi Britanik (British Pound)',
            'CHF': 'Franga Zvicerane (Swiss Franc)',
            'CAD': 'Canadian Dollar',
            'JPY': 'Japanese Yen',
            'AUD': 'Australian Dollar',
            'SEK': 'Swedish Krona',
            'NOK': 'Norwegian Krone',
            'DKK': 'Danish Krone',
        }
        
        return currency_names.get(currency_code, currency_code)
    
    def get_priority_rates(self) -> Optional[DailyExchangeRates]:
        """
        Get only the priority exchange rates (USD, EUR, GBP, CHF)
        
        Returns:
            DailyExchangeRates with only priority currencies
        """
        all_rates = self.get_current_rates()
        
        if not all_rates:
            return None
        
        # Filter to only priority currencies
        priority_rates = [
            rate for rate in all_rates.rates 
            if rate.currency_code in self.PRIORITY_CURRENCIES
        ]
        
        if not priority_rates:
            logger.warning("No priority currencies found in scraped rates")
            return None
        
        return DailyExchangeRates(
            date=all_rates.date,
            rates=priority_rates,
            source=all_rates.source
        )