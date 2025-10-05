"""
QuickBooks Online API client
"""

from quickbooks import QuickBooks
from quickbooks.objects import ExchangeRate as QBExchangeRate
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal

from ..utils.logger import get_logger

logger = get_logger(__name__)


class QuickBooksClient:
    """QuickBooks Online API client wrapper"""
    
    def __init__(self, 
                 client_id: str,
                 client_secret: str,
                 access_token: str,
                 refresh_token: str,
                 company_id: str,
                 sandbox: bool = True):
        """
        Initialize QuickBooks client
        
        Args:
            client_id: QB app client ID
            client_secret: QB app client secret
            access_token: User access token
            refresh_token: User refresh token
            company_id: Company ID
            sandbox: Whether to use sandbox environment
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.company_id = company_id
        self.sandbox = sandbox
        
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the QuickBooks client"""
        try:
            self._client = QuickBooks(
                sandbox=self.sandbox,
                consumer_key=self.client_id,
                consumer_secret=self.client_secret,
                access_token=self.access_token,
                access_token_secret=self.refresh_token,
                company_id=self.company_id
            )
            logger.info("QuickBooks client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize QuickBooks client: {str(e)}")
            raise
    
    def test_connection(self) -> bool:
        """
        Test the connection to QuickBooks API
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Try to get company info as a connection test
            company_info = self._client.get_company_info()
            logger.info(f"Connected to QuickBooks company: {company_info}")
            return True
        except Exception as e:
            logger.error(f"QuickBooks connection test failed: {str(e)}")
            return False
    
    def get_existing_exchange_rates(self, target_date: date) -> List[Dict[str, Any]]:
        """
        Get existing exchange rates for a specific date
        
        Args:
            target_date: Date to query
            
        Returns:
            List of existing exchange rate records
        """
        try:
            # Query exchange rates for the specific date
            date_str = target_date.strftime("%Y-%m-%d")
            
            # Note: The exact query syntax may vary based on QB API version
            query = f"SELECT * FROM ExchangeRate WHERE AsOfDate = '{date_str}'"
            
            results = self._client.query(query)
            return results or []
            
        except Exception as e:
            logger.error(f"Error querying existing exchange rates: {str(e)}")
            return []
    
    def create_exchange_rate(self, 
                           source_currency: str,
                           target_currency: str,
                           rate: Decimal,
                           as_of_date: date) -> Optional[str]:
        """
        Create or update an exchange rate in QuickBooks
        
        Args:
            source_currency: Source currency code (e.g., 'USD')
            target_currency: Target currency code (e.g., 'ALL')
            rate: Exchange rate
            as_of_date: Date of the rate
            
        Returns:
            Exchange rate ID if successful, None otherwise
        """
        try:
            # Create QB exchange rate object
            qb_rate = QBExchangeRate()
            qb_rate.SourceCurrencyCode = source_currency
            qb_rate.TargetCurrencyCode = target_currency
            qb_rate.Rate = float(rate)
            qb_rate.AsOfDate = as_of_date.strftime("%Y-%m-%d")
            
            # Save to QuickBooks
            result = qb_rate.save(qb=self._client)
            
            if result:
                logger.info(f"Created exchange rate: {source_currency}/{target_currency} = {rate}")
                return str(result.Id)
            else:
                logger.error("Failed to create exchange rate")
                return None
                
        except Exception as e:
            logger.error(f"Error creating exchange rate: {str(e)}")
            return None
    
    def update_exchange_rate(self,
                           rate_id: str,
                           rate: Decimal,
                           as_of_date: date) -> bool:
        """
        Update an existing exchange rate
        
        Args:
            rate_id: Exchange rate ID
            rate: New exchange rate
            as_of_date: Date of the rate
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get existing rate
            existing_rate = QBExchangeRate.get(rate_id, qb=self._client)
            
            if existing_rate:
                existing_rate.Rate = float(rate)
                existing_rate.AsOfDate = as_of_date.strftime("%Y-%m-%d")
                
                result = existing_rate.save(qb=self._client)
                
                if result:
                    logger.info(f"Updated exchange rate ID {rate_id}: rate = {rate}")
                    return True
                else:
                    logger.error(f"Failed to update exchange rate ID {rate_id}")
                    return False
            else:
                logger.error(f"Exchange rate ID {rate_id} not found")
                return False
                
        except Exception as e:
            logger.error(f"Error updating exchange rate: {str(e)}")
            return False
    
    def get_currencies(self) -> List[Dict[str, str]]:
        """
        Get list of available currencies in QuickBooks
        
        Returns:
            List of currency dictionaries
        """
        try:
            # Query all items (currencies are items in QB)
            query = "SELECT * FROM Item WHERE Type = 'Currency'"
            results = self._client.query(query)
            
            currencies = []
            for item in results:
                currencies.append({
                    'code': item.get('Name', ''),
                    'name': item.get('Description', ''),
                    'id': item.get('Id', '')
                })
            
            return currencies
            
        except Exception as e:
            logger.error(f"Error getting currencies: {str(e)}")
            return []
    
    def refresh_tokens(self) -> bool:
        """
        Refresh access tokens
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # This would implement token refresh logic
            # The exact implementation depends on the QB OAuth flow
            logger.info("Token refresh not implemented yet")
            return False
        except Exception as e:
            logger.error(f"Error refreshing tokens: {str(e)}")
            return False