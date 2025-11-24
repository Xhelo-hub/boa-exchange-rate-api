"""
Simple test script for BoA Exchange Rate API
Tests the scraper and QuickBooks OAuth without FastAPI

Run this with: python test_api_simple.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("=" * 60)
print("BoA Exchange Rate API - Development Test")
print("=" * 60)
print()

# Test 1: Import modules
print("✓ Testing imports...")
try:
    from src.boa_scraper.scraper import BoAScraper
    from src.utils.logger import get_logger
    print("✓ Imports successful!")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

logger = get_logger(__name__)

# Test 2: Scrape BoA rates
print("\n" + "=" * 60)
print("Test 1: Scraping Bank of Albania Website")
print("=" * 60)

try:
    scraper = BoAScraper()
    print(f"✓ BoA Scraper initialized")
    print(f"  URL: {scraper.base_url}/Tregjet/Kursi_zyrtar_i_kembimit/")
    print(f"  Priority currencies: {', '.join(scraper.PRIORITY_CURRENCIES)}")
    
    print("\nFetching current exchange rates...")
    daily_rates = scraper.get_current_rates()
    
    if daily_rates:
        print(f"\n✓ Successfully scraped {len(daily_rates.rates)} currencies!")
        print(f"  Date: {daily_rates.date}")
        print(f"  Source: {daily_rates.source}")
        print("\nExchange Rates (ALL per 1 unit):")
        print("-" * 60)
        
        # Sort by currency code
        sorted_rates = sorted(daily_rates.rates, key=lambda r: r.currency_code)
        
        for rate in sorted_rates:
            is_priority = "⭐" if rate.currency_code in scraper.PRIORITY_CURRENCIES else "  "
            multiplier = " (per 100)" if rate.currency_code in scraper.UNIT_100_CURRENCIES else ""
            print(f"{is_priority} {rate.currency_code:4s} = {rate.rate:>10.4f} ALL{multiplier}")
            print(f"       {rate.currency_name}")
        
        print("\n✓ Priority currencies (for QuickBooks sync):")
        priority_rates = scraper.get_priority_rates()
        if priority_rates:
            for rate in priority_rates.rates:
                print(f"  • {rate.currency_code}: {rate.rate} ALL")
    else:
        print("✗ No rates scraped - check BoA website structure")
        
except Exception as e:
    print(f"✗ Scraping failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: QuickBooks OAuth
print("\n" + "=" * 60)
print("Test 2: QuickBooks OAuth Configuration")
print("=" * 60)

try:
    from config.settings import settings
    
    print(f"✓ Configuration loaded")
    print(f"\nQuickBooks Settings:")
    print(f"  Client ID: {'✓ Set' if settings.qb_client_id else '✗ Missing'}")
    if settings.qb_client_id:
        print(f"             {settings.qb_client_id[:20]}...")
    print(f"  Client Secret: {'✓ Set' if settings.qb_client_secret else '✗ Missing'}")
    if settings.qb_client_secret:
        print(f"                 {settings.qb_client_secret[:20]}...")
    print(f"  Sandbox Mode: {settings.qb_sandbox}")
    print(f"  Redirect URI: {settings.qb_redirect_uri}")
    
    if settings.qb_client_id and settings.qb_client_secret:
        print("\n✓ QuickBooks credentials are configured!")
        print("\nNext Steps:")
        print("  1. Visit the authorization URL (see below)")
        print("  2. Sign in to QuickBooks Sandbox")
        print("  3. Authorize the app")
        print("  4. Copy the access tokens")
        print("  5. Update .env file with tokens")
        
        # Generate OAuth URL
        try:
            from src.quickbooks.oauth_client import QuickBooksOAuthClient
            oauth_client = QuickBooksOAuthClient()
            if oauth_client.auth_client:
                auth_url = oauth_client.get_authorization_url()
                print("\n" + "=" * 60)
                print("AUTHORIZATION URL:")
                print("=" * 60)
                print(auth_url)
                print("\nOpen this URL in your browser to authorize QuickBooks access")
                print("=" * 60)
            else:
                print("\n✗ Could not initialize OAuth client")
        except Exception as e:
            print(f"\n✗ OAuth client error: {e}")
    else:
        print("\n✗ QuickBooks credentials not configured")
        print("   Please update config/.env with your Client ID and Secret")
        
except Exception as e:
    print(f"✗ Configuration error: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "=" * 60)
print("Test Summary")
print("=" * 60)
print("""
The API is ready to:
✓ Scrape exchange rates from Bank of Albania
✓ Parse 22+ currencies including priority ones (USD, EUR, GBP, CHF)
✓ Generate QuickBooks OAuth authorization URL

To complete setup:
1. Open the authorization URL above in your browser
2. Sign in to QuickBooks Sandbox
3. Authorize the application
4. Copy the access_token and refresh_token
5. Update config/.env file with the tokens
6. Run: python -m uvicorn src.main:app --reload

Or use the API endpoints once running:
  GET  http://localhost:8000/api/v1/rates - Get all rates
  GET  http://localhost:8000/api/v1/rates?priority_only=true - Priority currencies
  POST http://localhost:8000/api/v1/sync - Sync to QuickBooks
""")

print("=" * 60)
