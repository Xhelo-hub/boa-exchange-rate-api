"""
Tests for FastAPI endpoints
"""

import pytest
from fastapi.testclient import TestClient
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock, patch

from src.main import app
from src.boa_scraper.models import ExchangeRate, DailyExchangeRates

client = TestClient(app)


class TestAPIEndpoints:
    """Test FastAPI endpoints"""
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "boa-exchange-rate-api"
        assert data["version"] == "0.1.0"
    
    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data
    
    @patch('src.api.routes.BoAScraper')
    def test_get_current_rates_success(self, mock_scraper_class):
        """Test successful retrieval of current rates"""
        # Mock scraper
        mock_scraper = Mock()
        mock_rates = DailyExchangeRates(
            date=date.today(),
            rates=[
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
        )
        mock_scraper.get_current_rates.return_value = mock_rates
        mock_scraper_class.return_value = mock_scraper
        
        # Test
        response = client.get("/api/v1/rates")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["total_rates"] == 2
        assert len(data["rates"]) == 2
        assert data["rates"][0]["currency_code"] == "USD"
        assert data["rates"][1]["currency_code"] == "EUR"
    
    @patch('src.api.routes.BoAScraper')
    def test_get_current_rates_not_found(self, mock_scraper_class):
        """Test retrieval when no rates found"""
        # Mock scraper
        mock_scraper = Mock()
        mock_scraper.get_current_rates.return_value = None
        mock_scraper_class.return_value = mock_scraper
        
        # Test
        response = client.get("/api/v1/rates")
        
        # Assertions
        assert response.status_code == 404
        assert "No exchange rates found" in response.json()["detail"]
    
    @patch('src.api.routes.BoAScraper')
    def test_get_rates_for_date(self, mock_scraper_class):
        """Test getting rates for specific date"""
        # Mock scraper
        mock_scraper = Mock()
        target_date = date(2023, 10, 5)
        mock_rates = DailyExchangeRates(
            date=target_date,
            rates=[
                ExchangeRate(
                    currency_code='USD',
                    currency_name='US Dollar',
                    rate=Decimal('105.50'),
                    date=target_date
                )
            ]
        )
        mock_scraper.get_rates_for_date.return_value = mock_rates
        mock_scraper_class.return_value = mock_scraper
        
        # Test
        response = client.get("/api/v1/rates/2023-10-05")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["date"] == "2023-10-05"
        assert data["total_rates"] == 1
    
    @patch('src.api.routes.trigger_manual_update')
    def test_trigger_sync_success(self, mock_trigger):
        """Test successful manual sync trigger"""
        mock_trigger.return_value = True
        
        response = client.post("/api/v1/sync")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "completed successfully" in data["message"]
    
    @patch('src.api.routes.trigger_manual_update')
    def test_trigger_sync_failure(self, mock_trigger):
        """Test failed manual sync trigger"""
        mock_trigger.return_value = False
        
        response = client.post("/api/v1/sync")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "failed" in data["message"]
    
    @patch('src.api.routes.QuickBooksSync')
    def test_get_sync_status(self, mock_sync_class):
        """Test getting sync status"""
        mock_sync = Mock()
        mock_sync.get_sync_status.return_value = {
            'client_initialized': True,
            'connection_active': True,
            'credentials_configured': True,
            'last_sync': None
        }
        mock_sync_class.return_value = mock_sync
        
        response = client.get("/api/v1/sync/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["client_initialized"] is True
        assert data["connection_active"] is True
    
    def test_get_supported_currencies(self):
        """Test getting supported currencies"""
        response = client.get("/api/v1/currencies")
        
        assert response.status_code == 200
        data = response.json()
        assert "currencies" in data
        assert "total" in data
        assert data["base_currency"] == "ALL"
        assert len(data["currencies"]) > 0
    
    def test_invalid_date_format(self):
        """Test invalid date format in URL"""
        response = client.get("/api/v1/rates/invalid-date")
        
        assert response.status_code == 422  # Validation error