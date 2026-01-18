"""
Database migration: Add approval workflow columns to Company table
Run this script to update the existing database schema
"""

import sqlite3
from pathlib import Path
from datetime import datetime

# Database path
DB_PATH = Path(__file__).parent.parent / "data" / "boa_exchange_rates.db"


def migrate_database():
    """Add approval workflow columns and make company_id nullable"""
    print(f"Migrating database: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if we need to recreate the table
        cursor.execute("PRAGMA table_info(companies)")
        columns = {col[1]: col for col in cursor.fetchall()}
        
        # Check if company_id is NOT NULL
        company_id_col = columns.get('company_id')
        needs_recreation = company_id_col and company_id_col[3] == 1  # notnull = 1
        
        if needs_recreation:
            print("Recreating companies table to make company_id nullable...")
            
            # Get existing data
            cursor.execute("SELECT * FROM companies")
            existing_data = cursor.fetchall()
            
            # Get column names
            cursor.execute("PRAGMA table_info(companies)")
            old_columns = [col[1] for col in cursor.fetchall()]
            
            print(f"Backing up {len(existing_data)} existing companies...")
            
            # Rename old table
            cursor.execute("ALTER TABLE companies RENAME TO companies_old")
            
            # Create new table with company_id nullable
            cursor.execute("""
                CREATE TABLE companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id VARCHAR(50) UNIQUE,
                    company_name VARCHAR(255),
                    access_token TEXT,
                    refresh_token TEXT,
                    token_expires_at DATETIME,
                    approval_status VARCHAR(20) DEFAULT 'pending' NOT NULL,
                    approved_by INTEGER,
                    approved_at DATETIME,
                    rejection_reason TEXT,
                    client_id VARCHAR(255) NOT NULL,
                    client_secret VARCHAR(255) NOT NULL,
                    is_sandbox BOOLEAN DEFAULT 0,
                    home_currency VARCHAR(3) DEFAULT 'ALL',
                    is_active BOOLEAN DEFAULT 1,
                    sync_enabled BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    last_sync_at DATETIME,
                    contact_email VARCHAR(255),
                    contact_name VARCHAR(255),
                    business_name VARCHAR(255),
                    tax_id VARCHAR(50),
                    address TEXT,
                    phone VARCHAR(50)
                )
            """)
            
            # Copy data from old table
            if existing_data:
                # Build insert statement with all old columns
                placeholders = ','.join(['?' for _ in old_columns])
                cols = ','.join(old_columns)
                
                # Add new columns with defaults
                new_cols = []
                if 'approval_status' not in old_columns:
                    new_cols.append("approval_status")
                if 'business_name' not in old_columns:
                    new_cols.append("business_name")
                if 'tax_id' not in old_columns:
                    new_cols.append("tax_id")
                if 'address' not in old_columns:
                    new_cols.append("address")
                if 'phone' not in old_columns:
                    new_cols.append("phone")
                
                for row in existing_data:
                    # Convert row to dict
                    row_dict = dict(zip(old_columns, row))
                    
                    # Add default values for new columns
                    if 'approval_status' not in row_dict:
                        row_dict['approval_status'] = 'approved'
                    if 'approved_at' not in row_dict:
                        row_dict['approved_at'] = row_dict.get('created_at')
                    
                    # Insert into new table
                    cols_to_insert = list(row_dict.keys())
                    values_to_insert = [row_dict[col] for col in cols_to_insert]
                    placeholders = ','.join(['?' for _ in cols_to_insert])
                    
                    cursor.execute(
                        f"INSERT INTO companies ({','.join(cols_to_insert)}) VALUES ({placeholders})",
                        values_to_insert
                    )
                
                print(f"Migrated {len(existing_data)} companies")
            
            # Drop old table
            cursor.execute("DROP TABLE companies_old")
            
            print("✓ Table recreated successfully")
        else:
            # Just add missing columns
            print("Adding missing columns...")
            
            if 'approval_status' not in columns:
                cursor.execute("ALTER TABLE companies ADD COLUMN approval_status VARCHAR(20) DEFAULT 'pending' NOT NULL")
            if 'approved_by' not in columns:
                cursor.execute("ALTER TABLE companies ADD COLUMN approved_by INTEGER")
            if 'approved_at' not in columns:
                cursor.execute("ALTER TABLE companies ADD COLUMN approved_at DATETIME")
            if 'rejection_reason' not in columns:
                cursor.execute("ALTER TABLE companies ADD COLUMN rejection_reason TEXT")
            if 'business_name' not in columns:
                cursor.execute("ALTER TABLE companies ADD COLUMN business_name VARCHAR(255)")
            if 'tax_id' not in columns:
                cursor.execute("ALTER TABLE companies ADD COLUMN tax_id VARCHAR(50)")
            if 'address' not in columns:
                cursor.execute("ALTER TABLE companies ADD COLUMN address TEXT")
            if 'phone' not in columns:
                cursor.execute("ALTER TABLE companies ADD COLUMN phone VARCHAR(50)")
            
            # Update existing companies to approved
            cursor.execute("""
                UPDATE companies 
                SET approval_status = 'approved',
                    approved_at = created_at
                WHERE company_id IS NOT NULL
            """)
        
        conn.commit()
        print(f"\n✓ Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n✗ Migration failed: {str(e)}")
        raise
    
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_database()
