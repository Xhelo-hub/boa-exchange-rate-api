"""
Public company registration routes - for users to request access
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

from ..database.engine import get_db
from ..database.models import Company
from ..utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/register", tags=["registration"])


class CompanyRegistrationRequest(BaseModel):
    """Public company registration request"""
    business_name: str = Field(..., min_length=2, max_length=255, description="Legal business name")
    tax_id: Optional[str] = Field(None, max_length=50, description="NIPT or tax identification number")
    contact_name: str = Field(..., min_length=2, max_length=255, description="Contact person name")
    contact_email: EmailStr = Field(..., description="Contact email address")
    phone: Optional[str] = Field(None, max_length=50, description="Phone number")
    address: Optional[str] = Field(None, description="Business address")
    home_currency: str = Field(default="ALL", max_length=3, description="Home currency code")
    message: Optional[str] = Field(None, description="Additional message for admin")


class CompanyRegistrationResponse(BaseModel):
    """Response after registration"""
    success: bool
    message: str
    request_id: int


@router.post("/company", response_model=CompanyRegistrationResponse)
async def register_company(
    request: CompanyRegistrationRequest,
    db: Session = Depends(get_db)
):
    """
    Public endpoint for companies to request access to the BoA Exchange Rate API.
    
    After registration:
    1. Company status is 'pending'
    2. Admin must approve before company can connect to QuickBooks
    3. After approval, company receives email with OAuth connection link
    """
    try:
        # Check if company already exists with this email or tax_id
        existing = None
        if request.tax_id:
            existing = db.query(Company).filter(Company.tax_id == request.tax_id).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A company with this tax ID has already been registered."
                )
        
        existing_email = db.query(Company).filter(Company.contact_email == request.contact_email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A company with this email address has already been registered."
            )
        
        # Create pending company registration
        new_company = Company(
            business_name=request.business_name,
            tax_id=request.tax_id,
            contact_name=request.contact_name,
            contact_email=request.contact_email,
            phone=request.phone,
            address=request.address,
            home_currency=request.home_currency,
            approval_status='pending',
            is_active=False,  # Not active until approved
            sync_enabled=False,  # Cannot sync until connected to QB
            # OAuth fields remain NULL until connected
            client_id='',  # Will be set from global config after approval
            client_secret=''  # Will be set from global config after approval
        )
        
        db.add(new_company)
        db.commit()
        db.refresh(new_company)
        
        logger.info(f"New company registration: {request.business_name} (ID: {new_company.id})")
        
        return CompanyRegistrationResponse(
            success=True,
            message="Your registration request has been submitted successfully. An administrator will review your request and contact you via email.",
            request_id=new_company.id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering company: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register company: {str(e)}"
        )


@router.get("/status/{request_id}")
async def check_registration_status(request_id: int, db: Session = Depends(get_db)):
    """
    Check the status of a registration request
    """
    company = db.query(Company).filter(Company.id == request_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration request not found"
        )
    
    return {
        "request_id": company.id,
        "business_name": company.business_name,
        "status": company.approval_status,
        "submitted_at": company.created_at,
        "approved_at": company.approved_at,
        "can_connect": company.approval_status == 'approved' and company.is_active,
        "message": _get_status_message(company.approval_status)
    }


def _get_status_message(status: str) -> str:
    """Get user-friendly status message"""
    messages = {
        'pending': 'Your request is pending review by an administrator.',
        'approved': 'Your request has been approved! You can now connect to QuickBooks.',
        'rejected': 'Your request has been rejected. Please contact support for more information.'
    }
    return messages.get(status, 'Unknown status')
