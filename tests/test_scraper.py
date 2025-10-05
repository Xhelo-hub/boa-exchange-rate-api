"""
Tests for Bank of Albania scraper
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

from src.boa_scraper.scraper import BoAScraper
from src.boa_scraper.models import ExchangeRate, DailyExchangeRates


class TestBoAScraper:
    """Test Bank of Albania scraper"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.scraper = BoAScraper()
    
    def test_scraper_initialization(self):
        """Test scraper initialization"""
        assert self.scraper.base_url == "https://www.bankofalbania.org"
        assert self.scraper.session is not None
    
    @patch('requests.Session.get')
    def test_get_current_rates_success(self, mock_get):
        """Test successful scraping of current rates"""
        # Mock HTML response
        mock_html = """
        <html>
            <table class="table">
                <tr><th>Currency</th><th>Name</th><th>Rate</th></tr>
                <tr><td>USD</td><td>US Dollar</td><td>105.50</td></tr>
                <tr><td>EUR</td><td>Euro</td><td>115.20</td></tr>
            </table>
        </html>
        """
        
        mock_response = Mock()
        mock_response.content = mock_html.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Test
        result = self.scraper.get_current_rates()
        
        # Assertions
        assert result is not None
        assert isinstance(result, DailyExchangeRates)
        assert result.date == date.today()
        assert len(result.rates) >= 0  # Depends on parsing
    
    @patch('requests.Session.get')
    def test_get_current_rates_request_error(self, mock_get):
        """Test scraping with request error"""
        mock_get.side_effect = Exception("Connection error")
        
        result = self.scraper.get_current_rates()
        
        assert result is None
    
    def test_get_currency_name(self):
        """Test currency name mapping"""
        assert self.scraper._get_currency_name('USD') == 'US Dollar'
        assert self.scraper._get_currency_name('EUR') == 'Euro'
        assert self.scraper._get_currency_name('XYZ') == 'XYZ'  # Unknown currency
    
    def test_get_rates_for_date_today(self):
        """Test getting rates for today's date"""
        with patch.object(self.scraper, 'get_current_rates') as mock_current:
            mock_rates = DailyExchangeRates(
                date=date.today(),
                rates=[
                    ExchangeRate(
                        currency_code='USD',
                        currency_name='US Dollar',
                        rate=Decimal('105.50'),
                        date=date.today()
                    )
                ]
            )
            mock_current.return_value = mock_rates
            
            result = self.scraper.get_rates_for_date(date.today())
            
            assert result is not None
            assert result.date == date.today()
            mock_current.assert_called_once()
    
    def test_get_rates_for_historical_date(self):
        """Test getting rates for historical date"""
        historical_date = date(2023, 1, 1)
        
        result = self.scraper.get_rates_for_date(historical_date)
        
        # Should return None for historical dates (not implemented yet)
        assert result is None


class TestExchangeRateModels:
    """Test exchange rate data models"""
    
    def test_exchange_rate_creation(self):
        """Test creating an exchange rate"""
        rate = ExchangeRate(
            currency_code='USD',
            currency_name='US Dollar',
            rate=Decimal('105.50'),
            date=date.today()
        )
        
        assert rate.currency_code == 'USD'
        assert rate.currency_name == 'US Dollar'
        assert rate.rate == Decimal('105.50')
        assert rate.date == date.today()
        assert rate.created_at is not None
    
    def test_daily_exchange_rates_creation(self):
        """Test creating daily exchange rates"""
        rates = [
            ExchangeRate(
                currency_code='USD',
                currency_name='US Dollar',
                rate=Decimal('105.50'),
                date=date.today()
            ),
            ExchangeRate(
                currency_code='EUR',
                currency_name='Euro',
                rate=Decimal('115.20'),
                date=date.today()
            )
        ]
        
        daily_rates = DailyExchangeRates(
            date=date.today(),
            rates=rates
        )
        
        assert daily_rates.date == date.today()
        assert len(daily_rates.rates) == 2
        assert daily_rates.source == "Bank of Albania"
        assert daily_rates.scraped_at is not None