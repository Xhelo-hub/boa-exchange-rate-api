"""
Admin authentication schemas
"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, time
from typing import Optional, List


class AdminLogin(BaseModel):
    """Admin login request"""
    username: str
    password: str


class AdminCreate(BaseModel):
    """Create new admin"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    is_superadmin: bool = False


class AdminResponse(BaseModel):
    """Admin user response"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_superadmin: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


class AdminToken(BaseModel):
    """Admin JWT token response"""
    access_token: str
    token_type: str = "bearer"
    admin: AdminResponse


class GlobalSyncSettingsUpdate(BaseModel):
    """Update global sync settings"""
    schedule_enabled: Optional[bool] = None
    schedule_time: Optional[time] = None
    timezone: Optional[str] = None
    retry_on_failure: Optional[bool] = None
    max_retry_attempts: Optional[int] = Field(None, ge=1, le=10)
    retry_delay_minutes: Optional[int] = Field(None, ge=1, le=60)
    boa_timeout_seconds: Optional[int] = Field(None, ge=10, le=120)
    boa_retry_attempts: Optional[int] = Field(None, ge=1, le=5)
    auto_refresh_tokens: Optional[bool] = None
    token_refresh_threshold_hours: Optional[int] = Field(None, ge=1, le=72)
    notify_on_success: Optional[bool] = None
    notify_on_failure: Optional[bool] = None
    notification_email: Optional[EmailStr] = None
    enforce_global_schedule: Optional[bool] = None


class GlobalSyncSettingsResponse(BaseModel):
    """Global sync settings response"""
    id: int
    schedule_enabled: bool
    schedule_time: time
    timezone: str
    retry_on_failure: bool
    max_retry_attempts: int
    retry_delay_minutes: int
    boa_timeout_seconds: int
    boa_retry_attempts: int
    auto_refresh_tokens: bool
    token_refresh_threshold_hours: int
    notify_on_success: bool
    notify_on_failure: bool
    notification_email: Optional[str]
    enforce_global_schedule: bool
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CompanySyncSettingsUpdate(BaseModel):
    """Update company-specific sync settings"""
    use_custom_schedule: Optional[bool] = None
    schedule_time: Optional[time] = None
    timezone: Optional[str] = None
    enabled_currencies: Optional[List[str]] = None
    exclude_currencies: Optional[List[str]] = None
    sync_on_create: Optional[bool] = None
    auto_sync_enabled: Optional[bool] = None
    notification_email: Optional[EmailStr] = None
    notify_on_sync: Optional[bool] = None


class CompanySyncSettingsResponse(BaseModel):
    """Company sync settings response"""
    id: int
    company_id: str
    use_custom_schedule: bool
    schedule_time: Optional[time]
    timezone: Optional[str]
    enabled_currencies: Optional[str]
    exclude_currencies: Optional[str]
    sync_on_create: bool
    auto_sync_enabled: bool
    notification_email: Optional[str]
    notify_on_sync: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CompanyManagementResponse(BaseModel):
    """Company with sync settings for admin dashboard"""
    company_id: str
    company_name: Optional[str]
    is_active: bool
    is_sandbox: bool
    sync_enabled: bool
    created_at: datetime
    last_sync: Optional[datetime]
    sync_settings: Optional[CompanySyncSettingsResponse]
    
    class Config:
        from_attributes = True


class ActivityLogResponse(BaseModel):
    """Admin activity log response"""
    id: int
    admin_username: str
    action: str
    target_type: Optional[str]
    target_id: Optional[str]
    details: Optional[str]
    ip_address: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class BulkOperationRequest(BaseModel):
    """Bulk operation on multiple companies"""
    company_ids: List[str] = Field(..., min_items=1)
    operation: str = Field(..., description="Operation to perform: sync_enable, sync_disable, sync_now, update_settings")
    settings: Optional[CompanySyncSettingsUpdate] = None


class BulkOperationResult(BaseModel):
    """Result of bulk operation"""
    company_id: str
    success: bool
    message: str


class BulkOperationResponse(BaseModel):
    """Bulk operation response"""
    total: int
    successful: int
    failed: int
    results: List[BulkOperationResult]
