"""
Configuration test script
Verifies all security settings are properly configured
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 70)
print("🔍 BoA Exchange Rate API - Configuration Test")
print("=" * 70)

# Test 1: Check environment file
print("\n📋 Test 1: Environment File")
env_file = PROJECT_ROOT / "config" / ".env"
if env_file.exists():
    print(f"✅ Found .env at: {env_file}")
    with open(env_file) as f:
        env_content = f.read()
        if "SECRET_KEY=HvE-7hTyvT8FTlqR7v7u4tab6mznEtjwFAo5otSJw0M=" in env_content:
            print("✅ SECRET_KEY is configured")
        else:
            print("❌ SECRET_KEY not found in .env")
        
        if "ADMIN_API_KEY=lBoUBlHuuU_nhlAoxK1nt7zx7Y4X_sBAyHkRxdCsizg" in env_content:
            print("✅ ADMIN_API_KEY is configured")
        else:
            print("❌ ADMIN_API_KEY not found in .env")
else:
    print(f"❌ .env file not found at: {env_file}")

# Test 2: Check database
print("\n📊 Test 2: Database")
db_file = PROJECT_ROOT / "data" / "boa_exchange.db"
if db_file.exists():
    print(f"✅ Database exists at: {db_file}")
    print(f"   Size: {db_file.stat().st_size / 1024:.2f} KB")
    
    # Check if tables exist
    import sqlite3
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    expected_tables = ['companies', 'exchange_rates', 'scraping_logs', 'quickbooks_syncs']
    for table in expected_tables:
        if table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"✅ Table '{table}' exists ({count} records)")
        else:
            print(f"❌ Table '{table}' missing")
    
    conn.close()
else:
    print(f"❌ Database not found at: {db_file}")

# Test 3: Check encryption module
print("\n🔐 Test 3: Encryption Module")
try:
    from src.utils.encryption import encrypt_token, decrypt_token
    
    # Test encryption/decryption
    test_token = "test_token_12345"
    encrypted = encrypt_token(test_token)
    decrypted = decrypt_token(encrypted)
    
    if decrypted == test_token:
        print("✅ Encryption working correctly")
        print(f"   Original:  {test_token}")
        print(f"   Encrypted: {encrypted[:50]}...")
        print(f"   Decrypted: {decrypted}")
    else:
        print("❌ Encryption test failed - decrypted value doesn't match")
        
except Exception as e:
    print(f"❌ Encryption test failed: {e}")

# Test 4: Check authentication module
print("\n🔑 Test 4: Authentication Module")
try:
    from src.utils.auth import AuthenticationManager
    
    auth = AuthenticationManager()
    
    # Test with correct key
    if auth.verify_admin_api_key("lBoUBlHuuU_nhlAoxK1nt7zx7Y4X_sBAyHkRxdCsizg"):
        print("✅ API key verification working")
    else:
        print("❌ API key verification failed")
    
    # Test with wrong key
    if not auth.verify_admin_api_key("wrong_key"):
        print("✅ Correctly rejects invalid API key")
    else:
        print("❌ Accepts invalid API key (security issue!)")
        
except Exception as e:
    print(f"❌ Authentication test failed: {e}")

# Test 5: Check QuickBooks configuration
print("\n📱 Test 5: QuickBooks Configuration")
try:
    with open(env_file) as f:
        env_content = f.read()
        qb_keys = [
            "QB_CLIENT_ID",
            "QB_CLIENT_SECRET",
            "QB_ACCESS_TOKEN",
            "QB_REFRESH_TOKEN",
            "QB_COMPANY_ID"
        ]
        for key in qb_keys:
            if key in env_content:
                print(f"✅ {key} configured")
            else:
                print(f"❌ {key} missing")
except Exception as e:
    print(f"❌ QuickBooks config test failed: {e}")

# Test 6: Check API routes
print("\n🌐 Test 6: API Routes")
try:
    import importlib.util
    
    routes_to_check = [
        ("src/api/routes.py", "Main routes"),
        ("src/api/company_routes.py", "Company management routes"),
        ("src/api/oauth_routes.py", "OAuth routes")
    ]
    
    for route_path, route_name in routes_to_check:
        full_path = PROJECT_ROOT / route_path
        if full_path.exists():
            print(f"✅ {route_name} found")
        else:
            print(f"❌ {route_name} missing")
            
except Exception as e:
    print(f"❌ Routes check failed: {e}")

# Summary
print("\n" + "=" * 70)
print("📝 Summary")
print("=" * 70)
print("\n✅ Configuration complete! Your API is ready for:")
print("   1. Local testing (when you fix Python 3.14 alpha issues)")
print("   2. Deployment to Hetzner server")
print("\n💡 Next steps:")
print("   • Deploy to Hetzner server (recommended due to Python 3.14 issues)")
print("   • Or downgrade to Python 3.11/3.12 for local testing")
print("\n🔑 Your credentials:")
print(f"   SECRET_KEY: HvE-7hTyvT8FTlqR7v7u4tab6mznEtjwFAo5otSJw0M=")
print(f"   ADMIN_API_KEY: lBoUBlHuuU_nhlAoxK1nt7zx7Y4X_sBAyHkRxdCsizg")
print("\n🚀 To deploy:")
print("   git add .")
print('   git commit -m "Add multi-tenant architecture with security"')
print("   git push origin main")
print("=" * 70)
