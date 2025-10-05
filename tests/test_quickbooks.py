"""
Tests for QuickBooks integration
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

from src.quickbooks.client import QuickBooksClient
from src.quickbooks.sync import QuickBooksSync
from src.boa_scraper.models import ExchangeRate, DailyExchangeRates


class TestQuickBooksClient:
    """Test QuickBooks Online client"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.client = QuickBooksClient(
            client_id="test_client_id",
            client_secret="test_client_secret",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            company_id="test_company_id",
            sandbox=True
        )
    
    def test_client_initialization(self):
        """Test client initialization"""
        assert self.client.client_id == "test_client_id"
        assert self.client.sandbox is True
        assert self.client.company_id == "test_company_id"
    
    @patch('src.quickbooks.client.QuickBooks')
    def test_test_connection_success(self, mock_qb_class):
        """Test successful connection test"""
        mock_qb = Mock()
        mock_qb.get_company_info.return_value = {"name": "Test Company"}
        mock_qb_class.return_value = mock_qb
        
        # Reinitialize to use the mock
        self.client._initialize_client()
        
        result = self.client.test_connection()
        
        assert result is True
    
    @patch('src.quickbooks.client.QuickBooks')
    def test_test_connection_failure(self, mock_qb_class):
        """Test connection test failure"""
        mock_qb = Mock()
        mock_qb.get_company_info.side_effect = Exception("Connection failed")
        mock_qb_class.return_value = mock_qb
        
        # Reinitialize to use the mock
        self.client._initialize_client()
        
        result = self.client.test_connection()
        
        assert result is False
    
    def test_create_exchange_rate(self):
        """Test creating exchange rate"""
        with patch.object(self.client, '_client') as mock_client:
            mock_rate = Mock()
            mock_rate.save.return_value = Mock(Id="123")
            
            with patch('src.quickbooks.client.QBExchangeRate', return_value=mock_rate):
                result = self.client.create_exchange_rate(
                    source_currency="USD",
                    target_currency="ALL",
                    rate=Decimal("105.50"),
                    as_of_date=date.today()
                )
                
                assert result == "123"
                mock_rate.save.assert_called_once()


class TestQuickBooksSync:
    """Test QuickBooks synchronization service"""
    
    def setup_method(self):
        """Setup test fixtures"""
        with patch('src.quickbooks.sync.settings') as mock_settings:
            mock_settings.qb_client_id = "test_id"
            mock_settings.qb_client_secret = "test_secret"
            mock_settings.qb_access_token = "test_token"
            mock_settings.qb_refresh_token = "test_refresh"
            mock_settings.qb_company_id = "test_company"
            mock_settings.qb_sandbox = True
            
            with patch('src.quickbooks.sync.QuickBooksClient'):
                self.sync_service = QuickBooksSync()
    
    def test_sync_service_initialization(self):
        """Test sync service initialization"""
        assert self.sync_service is not None
    
    def test_sync_rates_success(self):
        """Test successful rate synchronization"""
        # Create test data
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
        
        # Mock client
        mock_client = Mock()
        mock_client.get_existing_exchange_rates.return_value = []
        mock_client.create_exchange_rate.return_value = "123"
        
        self.sync_service.client = mock_client
        
        # Test
        result = self.sync_service.sync_rates(daily_rates)
        
        # Assertions
        assert result is True
        assert mock_client.create_exchange_rate.call_count == 2
    
    def test_sync_rates_no_client(self):
        """Test sync with no client initialized"""
        rates = [
            ExchangeRate(
                currency_code='USD',
                currency_name='US Dollar',
                rate=Decimal('105.50'),
                date=date.today()
            )
        ]
        
        daily_rates = DailyExchangeRates(
            date=date.today(),
            rates=rates
        )
        
        self.sync_service.client = None
        
        result = self.sync_service.sync_rates(daily_rates)
        
        assert result is False
    
    def test_get_sync_status(self):
        """Test getting sync status"""
        mock_client = Mock()
        mock_client.test_connection.return_value = True
        
        self.sync_service.client = mock_client
        
        status = self.sync_service.get_sync_status()
        
        assert status['client_initialized'] is True
        assert status['connection_active'] is True
        assert 'credentials_configured' in status