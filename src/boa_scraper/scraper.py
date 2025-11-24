"""
Bank of Albania exchange rate scraper

Implementation follows BoA Regulation No. 1, dated June 2, 2021
"On the method of calculating the official exchange rate fixing (fiksi)"

The official fixing methodology:
- Calculated daily 11:30-12:00 by Bank of Albania
- Based on quotes from 10 participating banks
- Excludes 2 highest and 2 lowest quotes
- Average of remaining quotes = official fixing
- USD is the reference currency
- Other currencies calculated via cross-rates against USD

Data available from BoA website:
- Main rate (fiksi) for 22+ currencies
- Buy/sell rates for USD and EUR
- Daily changes
- Last update timestamp
- Unit multipliers (JPY, HUF, RUB per 100 units)
"""

import requests
from bs4 import BeautifulSoup
from datetime import date, datetime
from typing import List, Optional, Dict, Tuple
from decimal import Decimal
import re

from .models import ExchangeRate, DailyExchangeRates
from ..utils.logger import get_logger

logger = get_logger(__name__)


class BoAScraper:
    """
    Bank of Albania exchange rate scraper
    
    Scrapes the official exchange rate fixing (fiksi) published by Bank of Albania
    according to Regulation No. 1/2021.
    
    Daily currencies (calculated every business day):
    - USD (Dollar Amerikan) - reference currency
    - EUR (Euro)
    - JPY (Jeni Japonez) - per 100 units
    - GBP (Paundi Britanik)
    - CHF (Franga Zvicerane)
    - AUD (Dollari Australiane)
    - CAD (Dollari Kanadez)
    - SEK (Korona Suedeze)
    - NOK (Korona Norvegjeze)
    - DKK (Korona Daneze)
    - TRY (Lira Turke)
    - CNY (Juani Kinez - onshore)
    - CNH (Juani Kinez - offshore)
    - SDR (Të drejtat speciale të tërheqjes - IMF)
    - XAU (Ari - per 1 onc)
    - XAG (Argjendi - per 1 onc)
    
    Bi-monthly currencies (calculated 15th and last business day):
    - BGN (Leva Bullgare)
    - HUF (Forinta Hungareze) - per 100 units
    - RUB (Rubla Ruse) - per 100 units
    - HRK (Kuna Kroate) - obsolete
    - CZK (Korona Çeke)
    - MKD (Dinari Maqedonas)
    """
    
    # Priority currencies - most needed for QuickBooks sync
    PRIORITY_CURRENCIES = ['USD', 'EUR', 'GBP', 'CHF']
    
    # Currencies quoted per 100 units (as per BoA regulation)
    UNIT_100_CURRENCIES = ['JPY', 'HUF', 'RUB']
    
    # Albanian to English currency name mapping (complete as per regulation)
    CURRENCY_NAME_MAPPING = {
        'Dollar Amerikan': 'USD',
        'Dollari Amerikan': 'USD',
        'Euro': 'EUR',
        'Poundi Britanik': 'GBP',
        'Paundi Britanik': 'GBP',
        'Franga Zvicerane': 'CHF',
        'Jeni Japonez': 'JPY',
        'Dollari Australiane': 'AUD',
        'Dollari Kanadez': 'CAD',
        'Korona Suedeze': 'SEK',
        'Korona Norvegjeze': 'NOK',
        'Korona Daneze': 'DKK',
        'Lira Turke': 'TRY',
        'Juani Kinez': 'CNY',
        'Leva Bullgare': 'BGN',
        'Forinta Hungareze': 'HUF',
        'Rubla Ruse': 'RUB',
        'Kuna Kroate': 'HRK',
        'Korona Çeke': 'CZK',
        'Dinari Maqedonas': 'MKD',
        'Ari': 'XAU',
        'Argjendi': 'XAG',
        'Argjend': 'XAG',
        'SDR': 'SDR',
        'Të drejtat speciale të tërheqjes': 'SDR',
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
        
        Scrapes from official BoA page: /Tregjet/Kursi_zyrtar_i_kembimit/
        
        Returns:
            DailyExchangeRates object or None if scraping fails
        """
        try:
            # Official BoA exchange rate page
            url = f"{self.base_url}/Tregjet/Kursi_zyrtar_i_kembimit/"
            
            logger.info(f"Scraping exchange rates from: {url}")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'  # Ensure proper Albanian character handling
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract metadata (last update timestamp)
            boa_timestamp = self._extract_last_update_time(soup)
            
            # Parse the exchange rates table
            rates = self._parse_exchange_table(soup)
            
            if rates:
                # Determine effective date from BoA timestamp or use today
                effective_date = boa_timestamp.date() if boa_timestamp else date.today()
                
                daily_rates = DailyExchangeRates(
                    date=effective_date,
                    rates=rates
                )
                logger.info(f"Successfully scraped {len(rates)} exchange rates for {effective_date}")
                
                if boa_timestamp:
                    logger.info(f"BoA last update: {boa_timestamp}")
                
                return daily_rates
            else:
                logger.warning("No exchange rates found on the page")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Request error while scraping BoA: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error scraping BoA exchange rates: {str(e)}", exc_info=True)
            return None
    
    def _extract_last_update_time(self, soup: BeautifulSoup) -> Optional[datetime]:
        """
        Extract "Përditesimi i fundit" (last update) timestamp from page
        
        Format: "21.11.2025 12:12:08" or similar
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            datetime object or None
        """
        try:
            # Look for timestamp pattern in text
            text = soup.get_text()
            
            # Pattern: DD.MM.YYYY HH:MM:SS
            pattern = r'(\d{1,2}\.\d{1,2}\.\d{4})\s+(\d{1,2}:\d{2}:\d{2})'
            match = re.search(pattern, text)
            
            if match:
                date_str = match.group(1)
                time_str = match.group(2)
                
                # Parse: 21.11.2025 12:12:08
                dt = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M:%S")
                logger.debug(f"Extracted BoA timestamp: {dt}")
                return dt
            
            return None
            
        except Exception as e:
            logger.warning(f"Could not extract last update timestamp: {e}")
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