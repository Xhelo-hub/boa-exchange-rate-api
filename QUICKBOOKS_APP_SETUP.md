# QuickBooks Sandbox App Installation Guide

## Prerequisites
- QuickBooks Developer Account at https://developer.intuit.com
- Sandbox company created in your developer account

## Step 1: Create App in QuickBooks Developer Portal

1. Go to https://developer.intuit.com/app/developer/myapps
2. Click **"Create an app"** or select your existing app
3. If creating new:
   - Select **"QuickBooks Online and Payments"**
   - Enter app name: **"Konsulence ExRate"** (or your preferred name)
   - Click **Create app**

## Step 2: Configure App Settings

### Development Settings (Keys & OAuth)
1. Go to your app dashboard → **"Keys & credentials"** tab
2. You should see:
   - **Client ID**: `ABEPLlYnocY649z9IcHXbffPgBgCKiBhKt0Y46dMBM1oWfDPMI` (already have this)
   - **Client Secret**: `RODndqTMZi9lcguiLNtDZzTjzej2wRoH6XmACDbz` (already have this)

### Redirect URIs
3. Scroll down to **"Redirect URIs"** section
4. Add: `http://localhost:8000/api/v1/callback`
5. Click **Save**

### Scopes
6. Ensure the following scope is enabled:
   - ✅ **Accounting** (com.intuit.quickbooks.accounting)

## Step 3: Get Test Company

### Option A: Use Existing Sandbox Company
1. Go to https://developer.intuit.com/app/developer/myapps
2. Click on your app
3. Go to **"Testing"** tab
4. You'll see available sandbox companies listed

### Option B: Create New Sandbox Company
1. Go to https://developer.intuit.com/app/developer/sandbox
2. Click **"Add Sandbox Test Company"**
3. Select company type (e.g., "Accountant")
4. Wait for creation (takes ~30 seconds)

## Step 4: Connect App to Sandbox Company

### Method 1: OAuth Playground (Easiest)
1. Go to https://developer.intuit.com/app/developer/playground
2. Select your app from dropdown
3. Select **"QuickBooks Online"**
4. Click **"Connect to QuickBooks"**
5. Sign in and select your sandbox company
6. Authorize the connection
7. Copy the:
   - **Access Token**
   - **Refresh Token**
   - **Realm ID** (Company ID)

### Method 2: Custom Authorization Flow (What we're doing)
1. Make sure the callback server is running:
   ```powershell
   python oauth_callback_server.py
   ```

2. Open authorization URL in browser:
   ```
   https://appcenter.intuit.com/connect/oauth2?client_id=ABEPLlYnocY649z9IcHXbffPgBgCKiBhKt0Y46dMBM1oWfDPMI&scope=com.intuit.quickbooks.accounting&redirect_uri=http://localhost:8000/api/v1/callback&response_type=code&state=security_token_12345
   ```

3. **Important**: Sign in with your **Intuit Developer Account** credentials
   - NOT your sandbox company credentials
   - This is your developer.intuit.com login

4. Select the sandbox company you want to connect

5. Click **"Authorize"** or **"Connect"**

6. The callback server will capture:
   - Authorization Code
   - Company ID (Realm ID)

7. Exchange authorization code for tokens (see next section)

## Step 5: Exchange Code for Tokens

Once you have the authorization code from Step 4:

```powershell
$auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("ABEPLlYnocY649z9IcHXbffPgBgCKiBhKt0Y46dMBM1oWfDPMI:RODndqTMZi9lcguiLNtDZzTjzej2wRoH6XmACDbz"))

$body = @{
    grant_type = "authorization_code"
    code = "YOUR_AUTHORIZATION_CODE_HERE"
    redirect_uri = "http://localhost:8000/api/v1/callback"
}

$response = Invoke-RestMethod -Uri "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer" -Method Post -Headers @{Authorization = "Basic $auth"; "Content-Type" = "application/x-www-form-urlencoded"} -Body $body

$response | ConvertTo-Json
```

## Step 6: Update Configuration

Add the tokens to `config/.env`:

```env
QB_ACCESS_TOKEN=your_access_token_here
QB_REFRESH_TOKEN=your_refresh_token_here
QB_COMPANY_ID=your_realm_id_here
```

## Step 7: Enable Multicurrency in Sandbox Company

**CRITICAL**: Before syncing exchange rates, you must enable multicurrency:

1. Sign in to your sandbox company at https://sandbox.qbo.intuit.com
2. Go to **Settings** (⚙️ gear icon) → **Account and Settings**
3. Click **Advanced** tab
4. Find **Currency** section
5. Click **Edit**
6. Check **"Multicurrency"**
7. Select **"ALL - Albanian Lek"** as home currency
8. Click **Save**
9. Click **Done**

⚠️ **Warning**: Multicurrency cannot be disabled once enabled!

## Troubleshooting

### "Connection Problem" Error
- Make sure callback server is running on port 8000
- Check that redirect URI is exactly: `http://localhost:8000/api/v1/callback`
- Verify redirect URI is saved in your app settings at developer.intuit.com

### "App Not Authorized" Error
- Make sure you're signing in with your **developer account** (not sandbox user)
- Verify your app has the "Accounting" scope enabled
- Check that your app is in "Development" mode

### "Invalid Client" Error
- Verify Client ID and Secret are correct
- Check that credentials match your app in developer.intuit.com

### Port 8000 Already in Use
- Stop any other services on port 8000
- Or modify the port in `oauth_callback_server.py` and update redirect URI

## Next Steps

Once configured:
1. Start the API: `python -m uvicorn src.main:app --reload` (requires stable Python version)
2. Test scraping: `GET http://localhost:8000/api/v1/rates`
3. Test sync: `POST http://localhost:8000/api/v1/sync`

## Resources

- QuickBooks Developer Portal: https://developer.intuit.com
- OAuth 2.0 Playground: https://developer.intuit.com/app/developer/playground
- API Documentation: https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/exchangerate
- Sandbox Companies: https://developer.intuit.com/app/developer/sandbox
