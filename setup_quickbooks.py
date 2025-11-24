"""
QuickBooks OAuth Authorization URL Generator
Simple script to get started with QuickBooks integration
"""

# Your QuickBooks App Credentials
CLIENT_ID = "ABEPLlYnocY649z9IcHXbffPgBgCKiBhKt0Y46dMBM1oWfDPMI"
CLIENT_SECRET = "RODndqTMZi9lcguiLNtDZzTjzej2wRoH6XmACDbz"
REDIRECT_URI = "http://localhost:8000/api/v1/callback"
SANDBOX = True

print("=" * 80)
print("QuickBooks OAuth Setup - Development Mode")
print("=" * 80)
print()
print("Client ID:", CLIENT_ID[:30] + "...")
print("Environment:", "SANDBOX" if SANDBOX else "PRODUCTION")
print("Redirect URI:", REDIRECT_URI)
print()

# Build authorization URL
base_url = "https://appcenter.intuit.com/connect/oauth2"
scope = "com.intuit.quickbooks.accounting"
response_type = "code"
state = "security_token_12345"

auth_url = (
    f"{base_url}?"
    f"client_id={CLIENT_ID}&"
    f"scope={scope}&"
    f"redirect_uri={REDIRECT_URI}&"
    f"response_type={response_type}&"
    f"state={state}"
)

print("=" * 80)
print("STEP 1: AUTHORIZE THE APP")
print("=" * 80)
print()
print("Open this URL in your browser:")
print()
print(auth_url)
print()
print("=" * 80)
print()

print("What will happen:")
print("1. You'll be redirected to QuickBooks login page")
print("2. Sign in with your Intuit/QuickBooks account")
print("3. Select a company (or create a test company)")
print("4. Authorize the app to access your data")
print("5. You'll be redirected back to:", REDIRECT_URI)
print()

print("The callback URL will contain:")
print("  - code: Authorization code (use this to get tokens)")
print("  - realmId: Company ID")
print("  - state: Security token")
print()

print("Example callback URL:")
print(f"{REDIRECT_URI}?code=AB11111111111&realmId=123456789&state=security_token_12345")
print()

print("=" * 80)
print("STEP 2: EXCHANGE CODE FOR TOKENS")
print("=" * 80)
print()
print("After authorization, copy the 'code' and 'realmId' from the callback URL")
print("Then run this command to get your access tokens:")
print()
print("curl -X POST https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer \\")
print("  -H 'Accept: application/json' \\")
print("  -H 'Content-Type: application/x-www-form-urlencoded' \\")
print(f"  -u '{CLIENT_ID}:{CLIENT_SECRET}' \\")
print("  -d 'grant_type=authorization_code&code=YOUR_CODE&redirect_uri=" + REDIRECT_URI + "'")
print()

print("Or use PowerShell:")
print()
print("$headers = @{")
print("    'Accept' = 'application/json'")
print("    'Content-Type' = 'application/x-www-form-urlencoded'")
print("}")
print(f"$auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes('{CLIENT_ID}:{CLIENT_SECRET}'))")
print("$headers['Authorization'] = 'Basic ' + $auth")
print("$body = @{")
print("    'grant_type' = 'authorization_code'")
print("    'code' = 'YOUR_CODE_HERE'")
print(f"    'redirect_uri' = '{REDIRECT_URI}'")
print("}")
print("Invoke-RestMethod -Uri 'https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer' -Method Post -Headers $headers -Body $body")
print()

print("=" * 80)
print("STEP 3: UPDATE .ENV FILE")
print("=" * 80)
print()
print("After getting tokens, update config/.env with:")
print()
print(f"QB_CLIENT_ID={CLIENT_ID}")
print(f"QB_CLIENT_SECRET={CLIENT_SECRET}")
print("QB_ACCESS_TOKEN=your_access_token_here")
print("QB_REFRESH_TOKEN=your_refresh_token_here")
print("QB_COMPANY_ID=your_realm_id_here")
print("QB_SANDBOX=True")
print()

print("=" * 80)
print("READY TO START!")
print("=" * 80)
print()
print("Once configured, the API can:")
print("  ✓ Scrape exchange rates from Bank of Albania")
print("  ✓ Store rates in local SQLite database")
print("  ✓ Sync rates to QuickBooks Online")
print("  ✓ Run automatically every day at 9 AM")
print()
print("=" * 80)
