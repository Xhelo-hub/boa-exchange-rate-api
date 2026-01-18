"""
Multi-tenant OAuth routes for QuickBooks integration
Handles OAuth flow for multiple companies
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from ..database.engine import get_db
from ..database.models import Company
from ..quickbooks.oauth_client import QuickBooksOAuthClient
from ..utils.auth import verify_admin_key
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/oauth", tags=["oauth"])


@router.get("/connect")
async def connect_quickbooks(request: Request, company_id: int = None, db: Session = Depends(get_db)):
    """
    Step 1: Redirect user to QuickBooks authorization page
    
    Usage: Company clicks "Connect to QuickBooks" button
    Query Parameters:
        company_id: Optional - ID of the approved company requesting connection
    Returns: Redirect to QuickBooks OAuth authorization
    """
    try:
        # If company_id provided, verify the company is approved
        if company_id:
            company = db.query(Company).filter(Company.id == company_id).first()
            if not company:
                error_html = """
                <html><body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1 style="color: #cc0000;">⚠ Company Not Found</h1>
                    <p>The company ID provided is invalid.</p>
                    <p>Please contact your administrator.</p>
                </body></html>
                """
                return HTMLResponse(content=error_html, status_code=404)
            
            if company.approval_status != 'approved':
                status_messages = {
                    'pending': 'Your registration is still pending approval.',
                    'rejected': f'Your registration was rejected. {company.rejection_reason or "Please contact support."}'
                }
                message = status_messages.get(company.approval_status, 'Invalid approval status')
                
                error_html = f"""
                <html><body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1 style="color: #cc0000;">⚠ Not Approved</h1>
                    <p>{message}</p>
                    <p>Please contact your administrator for more information.</p>
                </body></html>
                """
                return HTMLResponse(content=error_html, status_code=403)
        
        oauth_client = QuickBooksOAuthClient()
        
        # Store company_id in state parameter for retrieval in callback
        state = str(company_id) if company_id else "admin"
        
        # Generate authorization URL
        auth_url = oauth_client.get_authorization_url(state=state)
        
        logger.info(f"Generated OAuth authorization URL for company_id: {company_id}")
        
        return RedirectResponse(url=auth_url)
        
    except Exception as e:
        logger.error(f"Error initiating OAuth flow: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to initiate QuickBooks connection")


@router.get("/callback")
async def oauth_callback(
    code: str,
    realmId: str,
    state: str = None,
    db: Session = Depends(get_db)
):
    """
    Step 2: Handle OAuth callback from QuickBooks
    
    QuickBooks redirects here after user authorizes the app
    
    Query Parameters:
        code: Authorization code to exchange for tokens
        realmId: QuickBooks company ID
        state: CSRF protection token
        
    Returns: Success page or error
    """
    try:
        # Import encrypt_token here to avoid circular import issues
        from ..utils.encryption import encrypt_token
        
        # Validate state (implement CSRF protection)
        # if not validate_state(state):
        #     raise HTTPException(status_code=400, detail="Invalid state parameter")
        
        oauth_client = QuickBooksOAuthClient()
        
        # Exchange authorization code for tokens
        token_response = oauth_client.exchange_code_for_tokens(code, realmId)
        
        if not token_response:
            raise HTTPException(status_code=400, detail="Failed to obtain access token")
        
        # Calculate token expiration (QB access tokens expire in 1 hour by default)
        token_expires_at = datetime.utcnow() + timedelta(hours=1)
        
        # Get company_id from state parameter
        company_db_id = None
        if state and state != "admin":
            try:
                company_db_id = int(state)
            except:
                pass
        
        # Check if company already exists by realm_id
        existing_company = db.query(Company).filter(Company.company_id == realmId).first()
        
        # Check if company exists by database ID (from registration)
        if not existing_company and company_db_id:
            existing_company = db.query(Company).filter(Company.id == company_db_id).first()
        
        if existing_company:
            # Verify company is approved before connecting
            if existing_company.approval_status != 'approved':
                raise HTTPException(
                    status_code=403,
                    detail="Company must be approved by an administrator before connecting to QuickBooks"
                )
            
            # Update existing company's tokens (encrypted)
            existing_company.company_id = realmId  # Set QB realm_id
            existing_company.access_token = encrypt_token(token_response['access_token'])
            existing_company.refresh_token = encrypt_token(token_response['refresh_token'])
            existing_company.token_expires_at = token_expires_at
            existing_company.is_active = True
            existing_company.sync_enabled = True  # Enable sync after connection
            existing_company.updated_at = datetime.utcnow()
            
            logger.info(f"Updated tokens for existing company: {realmId}")
            message = "Successfully connected your QuickBooks company!"
            
        else:
            # Create new company record with encrypted tokens (admin-initiated connection)
            new_company = Company(
                company_id=realmId,
                access_token=encrypt_token(token_response['access_token']),
                refresh_token=encrypt_token(token_response['refresh_token']),
                token_expires_at=token_expires_at,
                client_id=settings.qb_client_id,
                client_secret=encrypt_token(settings.qb_client_secret),
                is_sandbox=settings.qb_sandbox,
                approval_status='approved',  # Auto-approve admin connections
                is_active=True,
                sync_enabled=True
            )
            
            db.add(new_company)
            logger.info(f"Created new company: {realmId}")
            message = "Successfully connected your QuickBooks company!"
        
        db.commit()
        
        # Return success page
        html_content = f"""
        <html>
            <head>
                <title>QuickBooks Connected</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        max-width: 600px;
                        margin: 100px auto;
                        padding: 40px;
                        text-align: center;
                        background-color: #f5f5f5;
                    }}
                    .success-box {{
                        background: white;
                        padding: 40px;
                        border-radius: 10px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    }}
                    h1 {{
                        color: #2ca01c;
                        margin-bottom: 20px;
                    }}
                    .company-id {{
                        background: #f0f0f0;
                        padding: 15px;
                        border-radius: 5px;
                        font-family: monospace;
                        margin: 20px 0;
                    }}
                    .note {{
                        color: #666;
                        font-size: 14px;
                        margin-top: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="success-box">
                    <h1>✓ {message}</h1>
                    <p>Your QuickBooks company has been connected to the BoA Exchange Rate service.</p>
                    <div class="company-id">
                        <strong>Company ID:</strong> {realmId}
                    </div>
                    <p>Exchange rates from the Bank of Albania will be automatically synced to your QuickBooks account daily.</p>
                    <div class="note">
                        <p>You can close this window and return to your application.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Error in OAuth callback: {str(e)}")
        
        error_html = f"""
        <html>
            <head>
                <title>Connection Error</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        max-width: 600px;
                        margin: 100px auto;
                        padding: 40px;
                        text-align: center;
                    }}
                    .error-box {{
                        background: #ffe6e6;
                        padding: 40px;
                        border-radius: 10px;
                        border: 2px solid #ff4444;
                    }}
                    h1 {{
                        color: #cc0000;
                    }}
                </style>
            </head>
            <body>
                <div class="error-box">
                    <h1>⚠ Connection Failed</h1>
                    <p>There was an error connecting your QuickBooks company.</p>
                    <p><strong>Error:</strong> {str(e)}</p>
                    <p>Please try again or contact support.</p>
                </div>
            </body>
        </html>
        """
        
        return HTMLResponse(content=error_html, status_code=500)


@router.get("/disconnect/{company_id}", dependencies=[Depends(verify_admin_key)])
async def disconnect_quickbooks(
    company_id: str,
    db: Session = Depends(get_db)
):
    """
    Disconnect a company from QuickBooks
    
    **Requires Authentication:** X-API-Key header
    
    Path Parameters:
        company_id: QuickBooks company ID (realm_id)
        
    Returns: Success message
    """
    try:
        company = db.query(Company).filter(Company.company_id == company_id).first()
        
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Revoke tokens with QuickBooks (optional but recommended)
        try:
            oauth_client = QuickBooksOAuthClient()
            oauth_client.revoke_token(company.refresh_token)
        except Exception as e:
            logger.warning(f"Failed to revoke tokens: {str(e)}")
        
        # Deactivate company (don't delete to preserve history)
        company.is_active = False
        company.sync_enabled = False
        company.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Disconnected company: {company_id}")
        
        return {
            "success": True,
            "message": "Company disconnected successfully",
            "company_id": company_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting company: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to disconnect company")


@router.get("/status/{company_id}")
async def get_connection_status(
    company_id: str,
    db: Session = Depends(get_db)
):
    """
    Get connection status for a company
    
    Path Parameters:
        company_id: QuickBooks company ID (realm_id)
        
    Returns: Connection status information
    """
    try:
        company = db.query(Company).filter(Company.company_id == company_id).first()
        
        if not company:
            return {
                "connected": False,
                "message": "Company not found"
            }
        
        # Check if token is expired
        token_expired = False
        if company.token_expires_at:
            token_expired = datetime.utcnow() >= company.token_expires_at
        
        return {
            "connected": company.is_active,
            "company_id": company.company_id,
            "company_name": company.company_name,
            "sync_enabled": company.sync_enabled,
            "token_expired": token_expired,
            "last_sync": company.last_sync_at.isoformat() if company.last_sync_at else None,
            "created_at": company.created_at.isoformat(),
            "updated_at": company.updated_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting connection status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get connection status")
