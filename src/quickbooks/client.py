"""
QuickBooks Online API client
"""

import requests
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
            company_id: Company ID (realm ID)
            sandbox: Whether to use sandbox environment
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.company_id = company_id
        self.sandbox = sandbox
        
        # Set base URL based on environment
        self.base_url = (
            "https://sandbox-quickbooks.api.intuit.com/v3" 
            if sandbox 
            else "https://quickbooks.api.intuit.com/v3"
        )
        
        # Initialize session with headers
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        logger.info(f"QuickBooks client initialized for company {company_id} ({'sandbox' if sandbox else 'production'})")
    
    def test_connection(self) -> bool:
        """
        Test the connection to QuickBooks API
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Try to get company info as a connection test
            url = f"{self.base_url}/company/{self.company_id}/companyinfo/{self.company_id}"
            response = self.session.get(url)
            response.raise_for_status()
            
            company_info = response.json()
            company_name = company_info.get('CompanyInfo', {}).get('CompanyName', 'Unknown')
            logger.info(f"Connected to QuickBooks company: {company_name}")
            return True
        except Exception as e:
            logger.error(f"QuickBooks connection test failed: {str(e)}")
            return False
    
    def get_existing_exchange_rate(self, 
                                   source_currency: str, 
                                   target_date: date) -> Optional[Dict[str, Any]]:
        """
        Get existing exchange rate for a specific currency and date
        
        Uses GET /company/<realmId>/exchangerate endpoint with query parameters.
        Per QB API docs: -currencycode is the desired currency code (required)
                        -yyyy-mm-dd is the desired effective date (if not specified, today's date is used)
        
        Args:
            source_currency: Source currency code (e.g., 'USD')
            target_date: Date to query
            
        Returns:
            Exchange rate data including SyncToken if found, None otherwise
            
        Example response:
        {
            "ExchangeRate": {
                "SyncToken": "0",
                "SourceCurrencyCode": "USD",
                "TargetCurrencyCode": "ALL",
                "Rate": 95.50,
                "AsOfDate": "2025-11-23",
                "MetaData": {
                    "CreateTime": "2025-11-23T10:00:00-08:00",
                    "LastUpdatedTime": "2025-11-23T10:00:00-08:00"
                }
            }
        }
        """
        try:
            # Use the GET /exchangerate endpoint with currency code and date
            date_str = target_date.strftime("%Y-%m-%d")
            url = f"{self.base_url}/company/{self.company_id}/exchangerate"
            params = {
                'sourcecurrencycode': source_currency,
                'asofdate': date_str
            }
            
            response = self.session.get(url, params=params)
            
            # 404 means no rate exists for this currency/date combo - that's ok
            if response.status_code == 404:
                logger.debug(f"No existing rate for {source_currency} on {date_str}")
                return None
            
            response.raise_for_status()
            data = response.json()
            exchange_rate = data.get('ExchangeRate')
            
            if exchange_rate:
                logger.debug(
                    f"Found existing rate for {source_currency} on {date_str}: "
                    f"Rate={exchange_rate.get('Rate')}, SyncToken={exchange_rate.get('SyncToken')}"
                )
            
            return exchange_rate
            
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"HTTP error querying exchange rate: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error querying existing exchange rate: {str(e)}")
            return None
    
    def get_existing_exchange_rates(self, target_date: date) -> List[Dict[str, Any]]:
        """
        Get existing exchange rates for a specific date (kept for compatibility)
        
        Args:
            target_date: Date to query
            
        Returns:
            List of existing exchange rate records
        """
        # Note: QB doesn't provide a query-all-rates-for-date endpoint
        # This would need to iterate through known currencies
        # For now, return empty list and handle per-currency queries
        return []
    
    def create_or_update_exchange_rate(self, 
                                       source_currency: str,
                                       target_currency: str,
                                       rate: Decimal,
                                       as_of_date: date) -> bool:
        """
        Create or update an exchange rate in QuickBooks
        
        Per QB API docs: POST /company/<realmId>/exchangerate creates/updates a rate
        
        QuickBooks Exchange Rate Object Requirements:
        - SourceCurrencyCode: Required (3 chars) - e.g., 'USD', 'EUR'
        - TargetCurrencyCode: Optional (3 chars) - defaults to Home Currency if not supplied
        - Rate: Required (Decimal) - exchange rate value
        - AsOfDate: Required (Date) - effective date in YYYY-MM-DD format
        - SyncToken: Required for update - version number for optimistic locking
        
        Important notes:
        - Setting exchange rate != 1 when SourceCurrencyCode=TargetCurrencyCode results in rate=1
        - Setting rate where SourceCurrencyCode = home currency results in validation error
        - Only the latest version of the object is maintained by QuickBooks Online
        
        Args:
            source_currency: Source currency code (e.g., 'USD')
            target_currency: Target currency code (e.g., 'ALL' for Albanian Lek)
                           Defaults to home currency if not supplied
            rate: Exchange rate (units of target currency per 1 unit of source)
            as_of_date: Effective date of the rate
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if rate already exists to get SyncToken
            existing_rate = self.get_existing_exchange_rate(source_currency, as_of_date)
            
            date_str = as_of_date.strftime("%Y-%m-%d")
            
            # Build request payload per QB API documentation
            # Mandatory fields: SourceCurrencyCode, Rate, AsOfDate
            payload = {
                "SourceCurrencyCode": source_currency,
                "Rate": float(rate),
                "AsOfDate": date_str
            }
            
            # TargetCurrencyCode is optional - defaults to home currency
            # Include it if provided and different from source
            if target_currency and target_currency != source_currency:
                payload["TargetCurrencyCode"] = target_currency
            
            # SyncToken is required for updates
            if existing_rate:
                # Updating existing rate - use existing SyncToken
                payload["SyncToken"] = existing_rate.get("SyncToken", "0")
                if "MetaData" in existing_rate:
                    payload["MetaData"] = existing_rate["MetaData"]
                logger.debug(f"Updating existing rate with SyncToken: {payload['SyncToken']}")
            else:
                # Creating new rate - SyncToken = "0"
                payload["SyncToken"] = "0"
                logger.debug("Creating new rate with SyncToken: 0")
            
            # POST to exchangerate endpoint (creates or updates based on SyncToken)
            url = f"{self.base_url}/company/{self.company_id}/exchangerate"
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            exchange_rate = result.get('ExchangeRate', {})
            new_sync_token = exchange_rate.get('SyncToken', 'unknown')
            
            logger.info(
                f"{'Updated' if existing_rate else 'Created'} exchange rate: "
                f"{source_currency}/{target_currency} = {rate} (as of {date_str}, SyncToken: {new_sync_token})"
            )
            return True
                
        except requests.HTTPError as e:
            error_detail = e.response.text
            logger.error(f"HTTP error creating/updating exchange rate: {error_detail}")
            
            # Log specific validation errors
            if "validation" in error_detail.lower():
                logger.error(
                    f"Validation error - check that {source_currency} is not the home currency "
                    f"and is in the active currency list"
                )
            
            return False
        except Exception as e:
            logger.error(f"Error creating/updating exchange rate: {str(e)}")
            return False
    
    def create_exchange_rate(self, 
                           source_currency: str,
                           target_currency: str,
                           rate: Decimal,
                           as_of_date: date) -> Optional[str]:
        """
        Create an exchange rate in QuickBooks (legacy method for compatibility)
        
        Args:
            source_currency: Source currency code
            target_currency: Target currency code
            rate: Exchange rate
            as_of_date: Date of the rate
            
        Returns:
            "success" if successful, None otherwise
        """
        success = self.create_or_update_exchange_rate(
            source_currency, target_currency, rate, as_of_date
        )
        return "success" if success else None
    
    def update_exchange_rate(self,
                           rate_id: str,
                           rate: Decimal,
                           as_of_date: date) -> bool:
        """
        Update an existing exchange rate (legacy method - now uses create_or_update)
        
        Args:
            rate_id: Exchange rate ID (not used in new implementation)
            rate: New exchange rate
            as_of_date: Date of the rate
            
        Returns:
            True if successful, False otherwise
        """
        # Note: The new QB API doesn't use rate_id for updates
        # It uses currency code + date combination
        # This method is kept for compatibility but logs a warning
        logger.warning(
            "update_exchange_rate called with rate_id. "
            "Consider using create_or_update_exchange_rate instead."
        )
        # Cannot update without knowing the currency code
        return False
    
    def get_active_currencies(self) -> List[Dict[str, str]]:
        """
        Get list of active currencies in QuickBooks company
        
        Per QB API: POST /company/<realmId>/query with "select * from companycurrency"
        
        Returns:
            List of active currency dictionaries
        """
        try:
            url = f"{self.base_url}/company/{self.company_id}/query"
            params = {'query': 'select * from companycurrency'}
            
            response = self.session.post(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            query_response = data.get('QueryResponse', {})
            company_currencies = query_response.get('CompanyCurrency', [])
            
            currencies = []
            for currency in company_currencies:
                if currency.get('Active', False):
                    currencies.append({
                        'code': currency.get('Code', ''),
                        'name': currency.get('Name', ''),
                        'id': currency.get('Id', '')
                    })
            
            logger.info(f"Retrieved {len(currencies)} active currencies")
            return currencies
            
        except Exception as e:
            logger.error(f"Error getting active currencies: {str(e)}")
            return []
    
    def add_currency(self, currency_code: str) -> bool:
        """
        Add a currency to the active currency list
        
        Per QB API: POST /company/<realmId>/companycurrency
        
        Args:
            currency_code: ISO 4217 currency code (e.g., 'USD', 'EUR')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.base_url}/company/{self.company_id}/companycurrency"
            payload = {"Code": currency_code}
            
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            currency = result.get('CompanyCurrency', {})
            logger.info(f"Added currency: {currency.get('Code')} - {currency.get('Name')}")
            return True
            
        except requests.HTTPError as e:
            if e.response.status_code == 400:
                # Currency might already exist
                logger.warning(f"Currency {currency_code} may already be active")
                return True
            logger.error(f"HTTP error adding currency: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Error adding currency: {str(e)}")
            return False
    
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