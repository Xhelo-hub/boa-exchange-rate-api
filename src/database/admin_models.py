"""
Admin and sync settings models
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Time, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, time
from .models import Base


class Admin(Base):
    """Admin users for the system"""
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_superadmin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    activity_logs = relationship("AdminActivityLog", back_populates="admin")


class AdminActivityLog(Base):
    """Log admin actions for audit trail"""
    __tablename__ = "admin_activity_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=False)
    action = Column(String, nullable=False)  # login, create_company, update_settings, etc.
    target_type = Column(String)  # company, settings, admin
    target_id = Column(String)
    details = Column(Text)
    ip_address = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    admin = relationship("Admin", back_populates="activity_logs")


class GlobalSyncSettings(Base):
    """Global sync settings that apply to all companies by default"""
    __tablename__ = "global_sync_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Schedule settings
    schedule_enabled = Column(Boolean, default=True)
    schedule_time = Column(Time, default=time(8, 0))  # 08:00 AM
    timezone = Column(String, default="Europe/Tirane")
    
    # Retry settings
    retry_on_failure = Column(Boolean, default=True)
    max_retry_attempts = Column(Integer, default=3)
    retry_delay_minutes = Column(Integer, default=5)
    
    # BoA scraper settings
    boa_timeout_seconds = Column(Integer, default=30)
    boa_retry_attempts = Column(Integer, default=3)
    
    # QuickBooks settings
    auto_refresh_tokens = Column(Boolean, default=True)
    token_refresh_threshold_hours = Column(Integer, default=24)
    
    # Notification settings
    notify_on_success = Column(Boolean, default=False)
    notify_on_failure = Column(Boolean, default=True)
    notification_email = Column(String)
    
    # Force all companies to use these settings
    enforce_global_schedule = Column(Boolean, default=False)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, ForeignKey("admins.id"))


class CompanySyncSettings(Base):
    """Per-company sync settings that override global settings"""
    __tablename__ = "company_sync_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(String, ForeignKey("companies.company_id"), unique=True, nullable=False)
    
    # Override schedule settings
    use_custom_schedule = Column(Boolean, default=False)
    schedule_time = Column(Time)
    timezone = Column(String)
    
    # Currency filtering
    enabled_currencies = Column(Text)  # JSON array of currency codes
    exclude_currencies = Column(Text)  # JSON array of currency codes to exclude
    
    # Sync options
    sync_on_create = Column(Boolean, default=True)  # Sync immediately after company creation
    auto_sync_enabled = Column(Boolean, default=True)
    
    # Notification overrides
    notification_email = Column(String)
    notify_on_sync = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="sync_settings")
