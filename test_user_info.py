"""
Test script for QuickBooks OAuth user info functionality
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from quickbooks.oauth_client import QuickBooksOAuthClient


def test_user_info():
    """Test getting user info from QuickBooks"""
    
    # Initialize the OAuth client
    oauth_client = QuickBooksOAuthClient()
    
    # Example 1: Using stored access token (from settings/environment)
    print("=== Test 1: Using stored access token ===")
    user_info = oauth_client.get_user_info()
    
    if user_info:
        print("✅ User info retrieved successfully!")
        print(f"User info: {user_info}")
    else:
        print("❌ Failed to retrieve user info with stored token")
    
    print("\n" + "="*50 + "\n")
    
    # Example 2: Using a specific access token
    print("=== Test 2: Using specific access token ===")
    
    # Replace 'EnterAccessTokenHere' with your actual access token
    access_token = 'EnterAccessTokenHere'
    
    if access_token != 'EnterAccessTokenHere':
        user_info = oauth_client.get_user_info(access_token=access_token)
        
        if user_info:
            print("✅ User info retrieved successfully!")
            print(f"User info: {user_info}")
        else:
            print("❌ Failed to retrieve user info with provided token")
    else:
        print("ℹ️  Please replace 'EnterAccessTokenHere' with your actual access token")
    
    print("\n" + "="*50 + "\n")
    
    # Example 3: Getting company info
    print("=== Test 3: Getting company info ===")
    company_info = oauth_client.get_company_info()
    
    if company_info:
        print("✅ Company info retrieved successfully!")
        print(f"Company: {company_info.get('Name', 'Unknown')}")
        print(f"Company ID: {company_info.get('Id', 'Unknown')}")
    else:
        print("❌ Failed to retrieve company info")


def show_usage_example():
    """Show example usage of the user info method"""
    
    print("=== Usage Example ===")
    print("""
# Basic usage with stored token:
from quickbooks.oauth_client import QuickBooksOAuthClient

oauth_client = QuickBooksOAuthClient()
user_info = oauth_client.get_user_info()

# Usage with specific access token:
user_info = oauth_client.get_user_info(access_token='your_access_token_here')

# The response will be a dictionary containing user information like:
{
    "sub": "1234567890",
    "email": "user@example.com",
    "email_verified": true,
    "given_name": "John",
    "family_name": "Doe",
    "name": "John Doe",
    "picture": "https://...",
    "iss": "https://oauth.platform.intuit.com/op/v1",
    "aud": "your_client_id"
}
""")


if __name__ == "__main__":
    print("QuickBooks OAuth User Info Test")
    print("="*40)
    
    try:
        # Show usage example
        show_usage_example()
        
        print("\n" + "="*40 + "\n")
        
        # Run tests
        test_user_info()
        
    except Exception as e:
        print(f"❌ Error running tests: {str(e)}")
        
        # Show configuration help
        print("\n=== Configuration Help ===")
        print("""
To use this functionality, make sure you have:

1. Set up your QuickBooks app credentials in the .env file:
   QB_CLIENT_ID=your_client_id
   QB_CLIENT_SECRET=your_client_secret
   QB_REDIRECT_URI=http://localhost:8000/callback
   QB_SANDBOX=true

2. Obtained access tokens through the OAuth flow:
   QB_ACCESS_TOKEN=your_access_token
   QB_REFRESH_TOKEN=your_refresh_token
   QB_COMPANY_ID=your_company_id

3. Installed the required packages:
   pip install intuit-oauth requests

For more information, see the QuickBooks OAuth documentation:
https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth_2.0
""")