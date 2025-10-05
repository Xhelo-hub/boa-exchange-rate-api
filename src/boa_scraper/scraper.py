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
                    
                    if len(cols) >= 3:  # Assuming: Currency, Name, Rate
                        try:
                            currency_code = cols[0].get_text(strip=True)
                            currency_name = cols[1].get_text(strip=True)
                            rate_text = cols[2].get_text(strip=True)
                            
                            # Clean and parse the rate
                            rate_text = re.sub(r'[^\d.,]', '', rate_text)
                            rate_text = rate_text.replace(',', '.')
                            
                            if rate_text and currency_code:
                                rate = Decimal(rate_text)
                                
                                exchange_rate = ExchangeRate(
                                    currency_code=currency_code,
                                    currency_name=currency_name,
                                    rate=rate,
                                    date=date.today()
                                )
                                
                                rates.append(exchange_rate)
                                
                        except (ValueError, IndexError) as e:
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
    
    def _get_currency_name(self, currency_code: str) -> str:
        """
        Get full currency name from currency code
        
        Args:
            currency_code: ISO 4217 currency code
            
        Returns:
            Full currency name
        """
        currency_names = {
            'USD': 'US Dollar',
            'EUR': 'Euro',
            'GBP': 'British Pound',
            'CHF': 'Swiss Franc',
            'CAD': 'Canadian Dollar',
            'JPY': 'Japanese Yen',
            'AUD': 'Australian Dollar',
            'SEK': 'Swedish Krona',
            'NOK': 'Norwegian Krone',
            'DKK': 'Danish Krone',
        }
        
        return currency_names.get(currency_code, currency_code)