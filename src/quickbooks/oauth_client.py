"""
QuickBooks OAuth2 Authentication Client
"""

from intuitlib.client import AuthClient
from intuitlib.enums import Scopes
from intuitlib.exceptions import AuthClientError
from typing import Optional, Dict, Any
import requests

from ..utils.logger import get_logger
from config.settings import settings

logger = get_logger(__name__)


class QuickBooksOAuthClient:
    """QuickBooks OAuth2 authentication client"""
    
    def __init__(self):
        self.auth_client = None
        self.initialize_client()
    
    def initialize_client(self) -> bool:
        """Initialize the OAuth client"""
        try:
            self.auth_client = AuthClient(
                client_id=settings.qb_client_id,
                client_secret=settings.qb_client_secret,
                redirect_uri=settings.qb_redirect_uri or "http://localhost:8000/callback",
                environment='sandbox' if settings.qb_sandbox else 'production',
                access_token=settings.qb_access_token,
                refresh_token=settings.qb_refresh_token,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to initialize OAuth client: {str(e)}")
            return False
    
    def get_authorization_url(self) -> str:
        """Get authorization URL for OAuth flow"""
        if not self.auth_client:
            raise Exception("OAuth client not initialized")
        
        try:
            auth_url = self.auth_client.get_authorization_url([Scopes.ACCOUNTING])
            logger.info("Generated authorization URL")
            return auth_url
        except Exception as e:
            logger.error(f"Error generating authorization URL: {str(e)}")
            raise
    
    def exchange_code_for_tokens(self, authorization_code: str, realm_id: str) -> Dict[str, str]:
        """Exchange authorization code for access tokens"""
        if not self.auth_client:
            raise Exception("OAuth client not initialized")
        
        try:
            self.auth_client.get_bearer_token(authorization_code, realm_id=realm_id)
            
            return {
                'access_token': self.auth_client.access_token,
                'refresh_token': self.auth_client.refresh_token,
                'realm_id': realm_id,
                'id_token': self.auth_client.id_token
            }
        except AuthClientError as e:
            logger.error(f"Auth error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Token exchange error: {str(e)}")
            raise
    
    def get_user_info(self, access_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get user information using access token
        
        Args:
            access_token: Access token to use (if None, uses stored token)
            
        Returns:
            User information dictionary or None if failed
        """
        try:
            # Use provided token or the stored one
            token = access_token or (self.auth_client.access_token if self.auth_client else None)
            
            if not token:
                logger.error("No access token available for user info request")
                return None
            
            # Create a new auth client instance for this request if needed
            if access_token and access_token != getattr(self.auth_client, 'access_token', None):
                temp_client = AuthClient(
                    client_id=settings.qb_client_id,
                    client_secret=settings.qb_client_secret,
                    redirect_uri=settings.qb_redirect_uri or "http://localhost:8000/callback",
                    environment='sandbox' if settings.qb_sandbox else 'production',
                    access_token=access_token,
                )
                response = temp_client.get_user_info()
            else:
                if not self.auth_client:
                    logger.error("OAuth client not initialized")
                    return None
                response = self.auth_client.get_user_info()
            
            if response and response.status_code == 200:
                user_info = response.json()
                logger.info("Successfully retrieved user information")
                return user_info
            else:
                logger.error(f"Failed to get user info: {response.status_code if response else 'No response'}")
                return None
                
        except AuthClientError as e:
            logger.error(f"Auth error getting user info: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error getting user info: {str(e)}")
            return None
    
    def refresh_token(self) -> bool:
        """Refresh the access token"""
        if not self.auth_client or not self.auth_client.refresh_token:
            logger.error("No refresh token available")
            return False
        
        try:
            self.auth_client.refresh()
            logger.info("Successfully refreshed access token")
            return True
        except AuthClientError as e:
            logger.error(f"Error refreshing token: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error refreshing token: {str(e)}")
            return False
    
    def revoke_token(self) -> bool:
        """Revoke the current access token"""
        if not self.auth_client:
            logger.error("OAuth client not initialized")
            return False
        
        try:
            result = self.auth_client.revoke()
            logger.info("Successfully revoked access token")
            return result
        except AuthClientError as e:
            logger.error(f"Error revoking token: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error revoking token: {str(e)}")
            return False
    
    def make_api_request(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None, realm_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Make an authenticated API request to QuickBooks
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            data: Request data for POST/PUT
            realm_id: Company ID (realm ID)
            
        Returns:
            Response data or None if failed
        """
        if not self.auth_client or not self.auth_client.access_token:
            logger.error("No valid access token available")
            return None
        
        company_id = realm_id or settings.qb_company_id
        if not company_id:
            logger.error("No company ID available")
            return None
        
        base_url = "https://sandbox-quickbooks.api.intuit.com" if settings.qb_sandbox else "https://quickbooks.api.intuit.com"
        url = f"{base_url}/v3/company/{company_id}/{endpoint}"
        
        headers = {
            'Authorization': f'Bearer {self.auth_client.access_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                logger.warning("Access token expired, attempting refresh")
                if self.refresh_token():
                    # Retry the request
                    headers['Authorization'] = f'Bearer {self.auth_client.access_token}'
                    try:
                        if method.upper() == 'GET':
                            response = requests.get(url, headers=headers, timeout=30)
                        elif method.upper() == 'POST':
                            response = requests.post(url, headers=headers, json=data, timeout=30)
                        response.raise_for_status()
                        return response.json()
                    except Exception as retry_e:
                        logger.error(f"Retry request failed: {str(retry_e)}")
                        return None
                else:
                    logger.error("Failed to refresh access token")
                    return None
            else:
                logger.error(f"HTTP error {response.status_code}: {str(e)}")
                return None
        except Exception as e:
            logger.error(f"Request error: {str(e)}")
            return None
    
    def get_company_info(self, realm_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get company information"""
        company_id = realm_id or settings.qb_company_id
        response = self.make_api_request(f'companyinfo/{company_id}', realm_id=realm_id)
        
        if response and 'QueryResponse' in response:
            company_info = response['QueryResponse'].get('CompanyInfo', [])
            return company_info[0] if company_info else None
        
        return None