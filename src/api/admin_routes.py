"""
Admin dashboard routes for managing companies and sync settings
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import json

from ..database.engine import get_db
from ..database.models import Company
from ..database.admin_models import Admin, AdminActivityLog, GlobalSyncSettings, CompanySyncSettings
from ..api.admin_schemas import (
    AdminLogin, AdminCreate, AdminResponse, AdminToken,
    GlobalSyncSettingsUpdate, GlobalSyncSettingsResponse,
    CompanySyncSettingsUpdate, CompanySyncSettingsResponse,
    CompanyManagementResponse, ActivityLogResponse,
    BulkOperationRequest, BulkOperationResponse, BulkOperationResult
)
from ..utils.admin_auth import (
    authenticate_admin, create_access_token, get_password_hash,
    get_current_admin, get_current_superadmin
)
from ..utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def log_activity(db: Session, admin: Admin, action: str, target_type: str = None, 
                 target_id: str = None, details: str = None, ip: str = None):
    """Log admin activity"""
    log = AdminActivityLog(
        admin_id=admin.id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
        ip_address=ip
    )
    db.add(log)
    db.commit()


# ==================== AUTHENTICATION ====================

@router.post("/login", response_model=AdminToken)
async def admin_login(
    login_data: AdminLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """Admin login endpoint"""
    admin = authenticate_admin(db, login_data.username, login_data.password)
    
    if not admin:
        logger.warning(f"Failed login attempt for username: {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    # Update last login
    admin.last_login = datetime.utcnow()
    db.commit()
    
    # Log activity
    log_activity(db, admin, "login", ip=request.client.host)
    
    # Create access token
    access_token = create_access_token(data={"sub": admin.username})
    
    logger.info(f"Admin logged in: {admin.username}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "admin": admin
    }


@router.post("/register", response_model=AdminResponse, dependencies=[Depends(get_current_superadmin)])
async def create_admin(
    admin_data: AdminCreate,
    request: Request,
    current_admin: Admin = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """Create new admin (superadmin only)"""
    # Check if username or email exists
    existing = db.query(Admin).filter(
        (Admin.username == admin_data.username) | (Admin.email == admin_data.email)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists"
        )
    
    # Create new admin
    new_admin = Admin(
        username=admin_data.username,
        email=admin_data.email,
        hashed_password=get_password_hash(admin_data.password),
        full_name=admin_data.full_name,
        is_superadmin=admin_data.is_superadmin
    )
    
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    
    # Log activity
    log_activity(db, current_admin, "create_admin", "admin", str(new_admin.id), 
                 f"Created admin: {new_admin.username}", request.client.host)
    
    logger.info(f"New admin created: {new_admin.username} by {current_admin.username}")
    
    return new_admin


@router.get("/me", response_model=AdminResponse)
async def get_current_admin_info(current_admin: Admin = Depends(get_current_admin)):
    """Get current admin information"""
    return current_admin


# ==================== COMPANY MANAGEMENT ====================

@router.get("/companies", response_model=List[CompanyManagementResponse])
async def list_companies(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all companies with their sync settings"""
    query = db.query(Company)
    
    if is_active is not None:
        query = query.filter(Company.is_active == is_active)
    
    companies = query.offset(skip).limit(limit).all()
    
    # Fetch sync settings for each company
    result = []
    for company in companies:
        # Skip companies without company_id (pending registrations shown in pending tab)
        if not company.company_id:
            continue
            
        sync_settings = db.query(CompanySyncSettings).filter(
            CompanySyncSettings.company_id == company.company_id
        ).first()
        
        result.append({
            "company_id": company.company_id,
            "company_name": company.company_name or "Not Set",
            "is_active": company.is_active,
            "is_sandbox": company.is_sandbox,
            "sync_enabled": company.sync_enabled,
            "created_at": company.created_at,
            "last_sync": company.last_sync_at,
            "sync_settings": sync_settings
        })
    
    return result


@router.get("/companies/{company_id}", response_model=CompanyManagementResponse)
async def get_company(
    company_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get company details"""
    company = db.query(Company).filter(Company.company_id == company_id).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    sync_settings = db.query(CompanySyncSettings).filter(
        CompanySyncSettings.company_id == company_id
    ).first()
    
    return {
        "company_id": company.company_id,
        "company_name": company.company_name,
        "is_active": company.is_active,
        "is_sandbox": company.is_sandbox,
        "sync_enabled": company.sync_enabled,
        "created_at": company.created_at,
        "last_sync": company.last_sync_at,
        "sync_settings": sync_settings
    }


@router.patch("/companies/{company_id}/toggle-sync")
async def toggle_company_sync(
    company_id: str,
    request: Request,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Enable/disable sync for a company"""
    company = db.query(Company).filter(Company.company_id == company_id).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    company.sync_enabled = not company.sync_enabled
    db.commit()
    
    # Log activity
    action = "enable_sync" if company.sync_enabled else "disable_sync"
    log_activity(db, current_admin, action, "company", company_id, ip=request.client.host)
    
    return {
        "company_id": company_id,
        "sync_enabled": company.sync_enabled,
        "message": f"Sync {'enabled' if company.sync_enabled else 'disabled'} for company"
    }


@router.delete("/companies/{company_id}")
async def deactivate_company(
    company_id: str,
    request: Request,
    current_admin: Admin = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """Deactivate a company (superadmin only)"""
    company = db.query(Company).filter(Company.company_id == company_id).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    company.is_active = False
    company.sync_enabled = False
    db.commit()
    
    # Log activity
    log_activity(db, current_admin, "deactivate_company", "company", company_id, ip=request.client.host)
    
    return {"message": "Company deactivated successfully"}


# ==================== GLOBAL SYNC SETTINGS ====================

@router.get("/settings/global", response_model=GlobalSyncSettingsResponse)
async def get_global_settings(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get global sync settings"""
    settings = db.query(GlobalSyncSettings).first()
    
    if not settings:
        # Create default settings
        settings = GlobalSyncSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return settings


@router.patch("/settings/global", response_model=GlobalSyncSettingsResponse)
async def update_global_settings(
    settings_update: GlobalSyncSettingsUpdate,
    request: Request,
    current_admin: Admin = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """Update global sync settings (superadmin only)"""
    settings = db.query(GlobalSyncSettings).first()
    
    if not settings:
        settings = GlobalSyncSettings()
        db.add(settings)
    
    # Update fields
    update_data = settings_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    settings.updated_by = current_admin.id
    db.commit()
    db.refresh(settings)
    
    # Log activity
    log_activity(db, current_admin, "update_global_settings", "settings", "global",
                 json.dumps(update_data), request.client.host)
    
    logger.info(f"Global settings updated by {current_admin.username}")
    
    return settings


# ==================== COMPANY SYNC SETTINGS ====================

@router.get("/settings/company/{company_id}", response_model=CompanySyncSettingsResponse)
async def get_company_settings(
    company_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get company-specific sync settings"""
    # Verify company exists
    company = db.query(Company).filter(Company.company_id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    settings = db.query(CompanySyncSettings).filter(
        CompanySyncSettings.company_id == company_id
    ).first()
    
    if not settings:
        # Create default settings for company
        settings = CompanySyncSettings(company_id=company_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return settings


@router.patch("/settings/company/{company_id}", response_model=CompanySyncSettingsResponse)
async def update_company_settings(
    company_id: str,
    settings_update: CompanySyncSettingsUpdate,
    request: Request,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update company-specific sync settings"""
    # Verify company exists
    company = db.query(Company).filter(Company.company_id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    settings = db.query(CompanySyncSettings).filter(
        CompanySyncSettings.company_id == company_id
    ).first()
    
    if not settings:
        settings = CompanySyncSettings(company_id=company_id)
        db.add(settings)
    
    # Update fields
    update_data = settings_update.dict(exclude_unset=True)
    
    # Handle list fields (currencies)
    if 'enabled_currencies' in update_data and update_data['enabled_currencies']:
        update_data['enabled_currencies'] = json.dumps(update_data['enabled_currencies'])
    if 'exclude_currencies' in update_data and update_data['exclude_currencies']:
        update_data['exclude_currencies'] = json.dumps(update_data['exclude_currencies'])
    
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    db.commit()
    db.refresh(settings)
    
    # Log activity
    log_activity(db, current_admin, "update_company_settings", "company", company_id,
                 json.dumps({k: str(v) for k, v in update_data.items()}), request.client.host)
    
    logger.info(f"Company {company_id} settings updated by {current_admin.username}")
    
    return settings


# ==================== ACTIVITY LOGS ====================

@router.get("/logs", response_model=List[ActivityLogResponse])
async def get_activity_logs(
    skip: int = 0,
    limit: int = 50,
    action: Optional[str] = None,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get admin activity logs"""
    query = db.query(AdminActivityLog).join(Admin)
    
    if action:
        query = query.filter(AdminActivityLog.action == action)
    
    logs = query.order_by(AdminActivityLog.created_at.desc()).offset(skip).limit(limit).all()
    
    return [
        {
            "id": log.id,
            "admin_username": log.admin.username,
            "action": log.action,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at
        }
        for log in logs
    ]


# ==================== BULK OPERATIONS ====================

@router.post("/companies/bulk", response_model=BulkOperationResponse)
async def bulk_company_operations(
    bulk_request: BulkOperationRequest,
    request: Request,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Perform bulk operations on multiple companies
    
    Operations:
    - sync_enable: Enable sync for selected companies
    - sync_disable: Disable sync for selected companies
    - sync_now: Trigger immediate sync for selected companies
    - update_settings: Apply same settings to selected companies
    """
    results = []
    successful = 0
    failed = 0
    
    for company_id in bulk_request.company_ids:
        try:
            company = db.query(Company).filter(Company.company_id == company_id).first()
            
            if not company:
                results.append(BulkOperationResult(
                    company_id=company_id,
                    success=False,
                    message="Company not found"
                ))
                failed += 1
                continue
            
            # Perform operation
            if bulk_request.operation == "sync_enable":
                company.sync_enabled = True
                message = "Sync enabled"
                
            elif bulk_request.operation == "sync_disable":
                company.sync_enabled = False
                message = "Sync disabled"
                
            elif bulk_request.operation == "sync_now":
                if not company.sync_enabled:
                    results.append(BulkOperationResult(
                        company_id=company_id,
                        success=False,
                        message="Sync is disabled for this company"
                    ))
                    failed += 1
                    continue
                
                # Import here to avoid circular imports
                from ..quickbooks.sync import sync_exchange_rates
                
                try:
                    result = await sync_exchange_rates(company_id, db)
                    message = f"Sync completed: {result.get('synced_count', 0)} rates synced"
                except Exception as sync_error:
                    results.append(BulkOperationResult(
                        company_id=company_id,
                        success=False,
                        message=f"Sync failed: {str(sync_error)}"
                    ))
                    failed += 1
                    continue
                    
            elif bulk_request.operation == "update_settings":
                if not bulk_request.settings:
                    results.append(BulkOperationResult(
                        company_id=company_id,
                        success=False,
                        message="No settings provided"
                    ))
                    failed += 1
                    continue
                
                # Get or create company settings
                settings = db.query(CompanySyncSettings).filter(
                    CompanySyncSettings.company_id == company_id
                ).first()
                
                if not settings:
                    settings = CompanySyncSettings(company_id=company_id)
                    db.add(settings)
                
                # Update settings
                update_data = bulk_request.settings.dict(exclude_unset=True)
                
                # Handle list fields (currencies)
                if 'enabled_currencies' in update_data and update_data['enabled_currencies']:
                    update_data['enabled_currencies'] = json.dumps(update_data['enabled_currencies'])
                if 'exclude_currencies' in update_data and update_data['exclude_currencies']:
                    update_data['exclude_currencies'] = json.dumps(update_data['exclude_currencies'])
                
                for field, value in update_data.items():
                    setattr(settings, field, value)
                
                message = "Settings updated"
                
            else:
                results.append(BulkOperationResult(
                    company_id=company_id,
                    success=False,
                    message=f"Unknown operation: {bulk_request.operation}"
                ))
                failed += 1
                continue
            
            db.commit()
            
            results.append(BulkOperationResult(
                company_id=company_id,
                success=True,
                message=message
            ))
            successful += 1
            
        except Exception as e:
            db.rollback()
            results.append(BulkOperationResult(
                company_id=company_id,
                success=False,
                message=f"Error: {str(e)}"
            ))
            failed += 1
            logger.error(f"Bulk operation error for company {company_id}: {str(e)}")
    
    # Log bulk activity
    log_activity(
        db, current_admin, f"bulk_{bulk_request.operation}",
        "companies", ",".join(bulk_request.company_ids),
        f"Success: {successful}, Failed: {failed}",
        request.client.host
    )
    
    logger.info(
        f"Bulk operation '{bulk_request.operation}' by {current_admin.username}: "
        f"{successful} successful, {failed} failed"
    )
    
    return BulkOperationResponse(
        total=len(bulk_request.company_ids),
        successful=successful,
        failed=failed,
        results=results
    )


# ==================== COMPANY APPROVAL ====================

@router.get("/pending-companies")
async def get_pending_companies(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get all companies pending approval or awaiting QuickBooks connection"""
    from config.settings import settings
    
    # Pending approval
    pending = db.query(Company).filter(Company.approval_status == 'pending').order_by(Company.created_at.desc()).all()
    
    # Approved but not connected to QuickBooks yet
    approved_not_connected = db.query(Company).filter(
        Company.approval_status == 'approved',
        Company.company_id == None
    ).order_by(Company.approved_at.desc()).all()
    
    pending_list = [
        {
            "id": company.id,
            "business_name": company.business_name,
            "tax_id": company.tax_id,
            "contact_name": company.contact_name,
            "contact_email": company.contact_email,
            "phone": company.phone,
            "address": company.address,
            "home_currency": company.home_currency,
            "requested_at": company.created_at,
            "status": company.approval_status,
            "approved_at": None,
            "oauth_link": None
        }
        for company in pending
    ]
    
    approved_list = [
        {
            "id": company.id,
            "business_name": company.business_name,
            "tax_id": company.tax_id,
            "contact_name": company.contact_name,
            "contact_email": company.contact_email,
            "phone": company.phone,
            "address": company.address,
            "home_currency": company.home_currency,
            "requested_at": company.created_at,
            "status": "approved_awaiting_connection",
            "approved_at": company.approved_at,
            "oauth_link": f"{settings.app_url}/api/v1/oauth/connect?company_id={company.id}"
        }
        for company in approved_not_connected
    ]
    
    return {
        "pending_companies": pending_list,
        "approved_not_connected": approved_list,
        "total_pending": len(pending_list),
        "total_approved": len(approved_list)
    }


@router.post("/approve-company/{company_id}")
async def approve_company(
    company_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Approve a pending company registration"""
    from config.settings import settings
    
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    if company.approval_status != 'pending':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Company is already {company.approval_status}"
        )
    
    # Approve the company
    company.approval_status = 'approved'
    company.approved_by = current_admin.id
    company.approved_at = datetime.utcnow()
    company.is_active = True  # Activate the company
    
    # Set QuickBooks credentials from global config
    company.client_id = settings.qb_client_id
    company.client_secret = settings.qb_client_secret
    company.is_sandbox = settings.qb_sandbox
    
    db.commit()
    
    # Log activity
    log_activity(
        db, current_admin,
        action="approve_company",
        target_type="company",
        target_id=str(company_id),
        details=f"Approved company: {company.business_name}",
        ip=request.client.host if request.client else None
    )
    
    logger.info(f"Admin {current_admin.username} approved company {company.business_name} (ID: {company_id})")
    
    # Generate OAuth connection link
    oauth_link = f"{settings.app_url}/api/v1/oauth/connect?company_id={company.id}"
    
    return {
        "success": True,
        "message": f"Company '{company.business_name}' has been approved",
        "company_id": company.id,
        "oauth_connection_link": oauth_link,
        "instructions": "Send this link to the company to connect their QuickBooks account"
    }


@router.post("/reject-company/{company_id}")
async def reject_company(
    company_id: int,
    request: Request,
    reason: str = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Reject a pending company registration"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    if company.approval_status != 'pending':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Company is already {company.approval_status}"
        )
    
    # Reject the company
    company.approval_status = 'rejected'
    company.rejection_reason = reason
    company.approved_by = current_admin.id
    company.approved_at = datetime.utcnow()
    
    db.commit()
    
    # Log activity
    log_activity(
        db, current_admin,
        action="reject_company",
        target_type="company",
        target_id=str(company_id),
        details=f"Rejected company: {company.business_name}. Reason: {reason}",
        ip=request.client.host if request.client else None
    )
    
    logger.info(f"Admin {current_admin.username} rejected company {company.business_name} (ID: {company_id})")
    
    return {
        "success": True,
        "message": f"Company '{company.business_name}' has been rejected",
        "company_id": company.id,
        "reason": reason
    }
