"""
Setup script to create initial admin user and initialize settings
Run this once to set up the admin dashboard
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from src.database.engine import get_db_manager
from src.database.models import Base
from src.database.admin_models import Admin, GlobalSyncSettings
from src.utils.admin_auth import get_password_hash
from datetime import time


def init_database():
    """Create all tables"""
    print("Creating database tables...")
    db_mgr = get_db_manager()
    Base.metadata.create_all(bind=db_mgr.engine)
    print("✓ Database tables created")
    return db_mgr


def create_default_admin(db: Session):
    """Create default superadmin"""
    existing = db.query(Admin).filter(Admin.username == "admin").first()
    
    if existing:
        print("ℹ Admin user already exists")
        return existing
    
    print("\n=== Creating Default Superadmin ===")
    username = input("Username [admin]: ").strip() or "admin"
    email = input("Email [admin@example.com]: ").strip() or "admin@example.com"
    password = input("Password: ").strip()
    
    if not password:
        password = "admin123"  # Default password
        print(f"⚠ Using default password: {password}")
    
    full_name = input("Full Name [Admin User]: ").strip() or "Admin User"
    
    admin = Admin(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        full_name=full_name,
        is_superadmin=True,
        is_active=True
    )
    
    db.add(admin)
    db.commit()
    db.refresh(admin)
    
    print(f"\n✓ Superadmin created successfully!")
    print(f"  Username: {admin.username}")
    print(f"  Email: {admin.email}")
    print(f"  ⚠ IMPORTANT: Change the password after first login!\n")
    
    return admin


def create_default_settings(db: Session):
    """Create default global sync settings"""
    existing = db.query(GlobalSyncSettings).first()
    
    if existing:
        print("ℹ Global settings already exist")
        return existing
    
    print("Creating default global sync settings...")
    
    settings = GlobalSyncSettings(
        schedule_enabled=True,
        schedule_time=time(8, 0),  # 08:00 AM
        timezone="Europe/Tirane",
        retry_on_failure=True,
        max_retry_attempts=3,
        retry_delay_minutes=5,
        boa_timeout_seconds=30,
        boa_retry_attempts=3,
        auto_refresh_tokens=True,
        token_refresh_threshold_hours=24,
        notify_on_success=False,
        notify_on_failure=True,
        enforce_global_schedule=False
    )
    
    db.add(settings)
    db.commit()
    db.refresh(settings)
    
    print("✓ Default global settings created")
    print(f"  Schedule Time: {settings.schedule_time}")
    print(f"  Timezone: {settings.timezone}")
    print(f"  Auto Refresh Tokens: {settings.auto_refresh_tokens}\n")
    
    return settings


def main():
    """Main setup function"""
    print("\n" + "="*60)
    print("  BoA Exchange Rate API - Admin Dashboard Setup")
    print("="*60 + "\n")
    
    try:
        # Initialize database
        db_mgr = init_database()
        
        # Create session
        with db_mgr.get_session() as db:
            # Create default admin
            create_default_admin(db)
            
            # Create default settings
            create_default_settings(db)
        
        print("="*60)
        print("  Setup Complete!")
        print("="*60)
        print("\nNext steps:")
        print("1. Start the server: python start_server.py")
        print("2. Login at: http://localhost:8000/docs")
        print("3. Use endpoint: POST /api/v1/admin/login")
        print("4. Access admin dashboard endpoints with Bearer token")
        print("\nAdmin Dashboard Features:")
        print("  • Manage companies: GET /api/v1/admin/companies")
        print("  • Global settings: GET /api/v1/admin/settings/global")
        print("  • Company settings: GET /api/v1/admin/settings/company/{id}")
        print("  • Activity logs: GET /api/v1/admin/logs")
        print()
            
    except Exception as e:
        print(f"\n❌ Setup failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
