#!/usr/bin/env python3
"""
Test script for QuickBooks multicurrency integration

This script tests the full flow:
1. Scrape exchange rates from BoA
2. Post rates to QuickBooks sandbox
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.boa_scraper.scraper import BoAScraper
from src.quickbooks.sync import QuickBooksSync
from src.quickbooks.client import QuickBooksClient
from config.settings import settings
from decimal import Decimal
from datetime import date


def test_scraper():
    """Test BoA scraper"""
    print("\n=== Testing BoA Scraper ===")
    scraper = BoAScraper()
    
    # Test all rates
    daily_rates = scraper.get_current_rates()
    
    if daily_rates:
        print(f"✓ Successfully scraped {len(daily_rates.rates)} rates")
        print(f"  Date: {daily_rates.date}")
        print(f"  Source: {daily_rates.source}")
        print("\nAll rates:")
        for rate in daily_rates.rates:
            print(f"  {rate.currency_code} ({rate.currency_name}): {rate.rate} ALL")
    else:
        print("✗ Failed to scrape rates")
    
    # Test priority rates
    print("\n=== Testing Priority Currencies ===")
    priority_rates = scraper.get_priority_rates()
    
    if priority_rates:
        print(f"✓ Successfully scraped {len(priority_rates.rates)} priority rates")
        print("\nPriority rates (USD, EUR, GBP, CHF):")
        for rate in priority_rates.rates:
            print(f"  {rate.currency_code}: {rate.rate} ALL")
        
        # Check if all priority currencies are present
        found_codes = {r.currency_code for r in priority_rates.rates}
        expected_codes = {'USD', 'EUR', 'GBP', 'CHF'}
        missing = expected_codes - found_codes
        
        if missing:
            print(f"⚠ Missing priority currencies: {missing}")
        else:
            print("✓ All priority currencies found")
            
        return priority_rates
    else:
        print("✗ Failed to scrape priority rates")
        return daily_rates if daily_rates else None


def test_qb_connection():
    """Test QuickBooks connection"""
    print("\n=== Testing QuickBooks Connection ===")
    
    if not settings.qb_client_id:
        print("✗ QuickBooks credentials not configured")
        print("  Please set QB_CLIENT_ID, QB_CLIENT_SECRET, etc. in config/.env")
        return False
    
    try:
        sync = QuickBooksSync()
        status = sync.get_sync_status()
        
        print(f"  Client initialized: {status['client_initialized']}")
        print(f"  Connection active: {status['connection_active']}")
        print(f"  Credentials configured: {status['credentials_configured']}")
        
        if status['connection_active']:
            print("✓ QuickBooks connection successful")
            return True
        else:
            print("✗ QuickBooks connection failed")
            return False
            
    except Exception as e:
        print(f"✗ Error testing connection: {e}")
        return False


def test_currency_management(client):
    """Test currency management"""
    print("\n=== Testing Currency Management ===")
    
    try:
        # Get active currencies
        currencies = client.get_active_currencies()
        print(f"✓ Retrieved {len(currencies)} active currencies")
        
        if currencies:
            print("\nActive currencies:")
            for curr in currencies[:5]:
                print(f"  {curr['code']} - {curr['name']}")
        
        # Try to add USD if not present
        print("\nAdding USD to active currencies...")
        success = client.add_currency('USD')
        
        if success:
            print("✓ USD added/confirmed in active currency list")
        else:
            print("✗ Failed to add USD")
        
        return True
        
    except Exception as e:
        print(f"✗ Error in currency management: {e}")
        return False


def test_exchange_rate_posting(client):
    """Test posting a single exchange rate"""
    print("\n=== Testing Exchange Rate Posting ===")
    
    try:
        # Post a test rate
        test_rate = Decimal('100.50')
        test_date = date.today()
        
        print(f"Posting test rate: USD/ALL = {test_rate} (as of {test_date})")
        
        success = client.create_or_update_exchange_rate(
            source_currency='USD',
            target_currency='ALL',
            rate=test_rate,
            as_of_date=test_date
        )
        
        if success:
            print("✓ Successfully posted exchange rate")
            
            # Verify it was posted
            existing = client.get_existing_exchange_rate('USD', test_date)
            if existing:
                print(f"✓ Verified rate in QuickBooks: {existing.get('Rate')}")
            
            return True
        else:
            print("✗ Failed to post exchange rate")
            return False
            
    except Exception as e:
        print(f"✗ Error posting rate: {e}")
        return False


def test_full_sync(daily_rates):
    """Test full synchronization"""
    print("\n=== Testing Full Sync ===")
    
    if not daily_rates:
        print("✗ No rates to sync")
        return False
    
    try:
        sync = QuickBooksSync()
        
        if not sync.client:
            print("✗ QuickBooks client not initialized")
            return False
        
        print(f"Syncing {len(daily_rates.rates)} rates to QuickBooks...")
        success = sync.sync_rates(daily_rates)
        
        if success:
            print("✓ Full sync completed successfully")
            return True
        else:
            print("⚠ Sync completed with some errors (check logs)")
            return False
            
    except Exception as e:
        print(f"✗ Error in full sync: {e}")
        return False


def main():
    """Run all tests"""
    print("="*60)
    print("QuickBooks Multicurrency Integration Test")
    print("="*60)
    
    # Test 1: Scrape BoA rates
    daily_rates = test_scraper()
    
    # Test 2: QB connection
    qb_connected = test_qb_connection()
    
    if not qb_connected:
        print("\n⚠ QuickBooks not configured - skipping QB tests")
        print("\nTo enable QuickBooks integration:")
        print("1. Get credentials from https://developer.intuit.com/")
        print("2. Add them to config/.env")
        print("3. Run this test again")
        return
    
    # Test 3: Create QB client for detailed tests
    try:
        from src.quickbooks.sync import QuickBooksSync
        sync = QuickBooksSync()
        client = sync.client
        
        if not client:
            print("\n✗ Could not create QB client")
            return
        
        # Test 4: Currency management
        test_currency_management(client)
        
        # Test 5: Single rate posting
        test_exchange_rate_posting(client)
        
        # Test 6: Full sync (only if we have rates)
        if daily_rates:
            test_full_sync(daily_rates)
        
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("Test completed")
    print("="*60)


if __name__ == '__main__':
    main()
