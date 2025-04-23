import os
import streamlit as st
from supabase import create_client, Client
from dotenv import load_dotenv
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from model import Base

# Load environment variables
load_dotenv()

#############################
# SQLite Database Functions #
#############################

# --- Setup the SQLite database ---
def init_db(db_path="sqlite:///samples.db"):
    """Initialize the database and create all tables"""
    engine = create_engine(db_path, echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)

# Create the session factory
SessionLocal = init_db()

@contextmanager
def get_db_session():
    """Context manager for database sessions"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def backup_sqlite_database(backup_dir="backups"):
    """Create a backup of the SQLite database"""
    import shutil
    from datetime import datetime
    
    # Create backup directory if it doesn't exist
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"samples_backup_{timestamp}.db")
    
    # Copy the database file
    try:
        shutil.copy2("samples.db", backup_file)
        print(f"Database backed up to {backup_file}")
        return True
    except Exception as e:
        print(f"Backup failed: {e}")
        return False

#############################
# Supabase Database Functions #
#############################

# Get Supabase credentials from environment variables or secrets
def get_supabase_credentials():
    """Get Supabase credentials from environment variables or Streamlit secrets"""
    # Try to get from Streamlit secrets first (for production)
    if hasattr(st, "secrets") and "supabase" in st.secrets:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        service_key = st.secrets.get("supabase", {}).get("service_key", key)
    else:
        # Fall back to environment variables (for development)
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        service_key = os.environ.get("SUPABASE_SERVICE_KEY", key)
    
    return url, key, service_key

# Create Supabase client
def get_supabase_client(use_service_key=False) -> Client:
    """Get a Supabase client instance"""
    url, key, service_key = get_supabase_credentials()
    
    # Use service key for admin operations if requested
    if use_service_key:
        return create_client(url, service_key)
    
    return create_client(url, key)

@contextmanager
def get_supabase_session(use_service_key=False):
    """Context manager for Supabase client sessions"""
    client = get_supabase_client(use_service_key)
    try:
        yield client
    except Exception as e:
        print(f"Supabase error: {e}")
        raise
    finally:
        # No explicit cleanup needed for Supabase client
        pass

def init_supabase_tables():
    """Initialize Supabase tables if they don't exist"""
    # This function would create tables in Supabase if they don't exist
    # For Supabase, we can use SQL or the Supabase dashboard to create tables
    # Here we'll just check if we can connect to Supabase
    try:
        with get_supabase_session(use_service_key=True) as supabase:
            # Test the connection
            response = supabase.table("users").select("count", count="exact").execute()
            print(f"Connected to Supabase successfully. User count: {response.count}")
            return True
    except Exception as e:
        print(f"Failed to connect to Supabase: {e}")
        return False

def backup_supabase_database(backup_dir="backups"):
    """
    Create a backup of the Supabase database
    
    For Supabase, you can use their built-in backup system or
    export data to JSON/CSV files
    """
    try:
        # Create backup directory if it doesn't exist
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # Generate backup filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export tables to JSON files
        tables = ["users", "freezers", "racks", "boxes", "samples", "sample_history"]
        
        with get_supabase_session(use_service_key=True) as supabase:
            for table in tables:
                response = supabase.table(table).select("*").execute()
                
                if hasattr(response, "data"):
                    import json
                    backup_file = os.path.join(backup_dir, f"{table}_backup_{timestamp}.json")
                    with open(backup_file, 'w') as f:
                        json.dump(response.data, f, indent=2)
                    
                    print(f"Table {table} backed up to {backup_file}")
        
        return True
    except Exception as e:
        print(f"Backup failed: {e}")
        return False

# Unified backup function that tries both methods
def backup_database(backup_dir="backups"):
    """Create a backup of the database (tries both SQLite and Supabase)"""
    sqlite_result = backup_sqlite_database(backup_dir)
    supabase_result = backup_supabase_database(backup_dir)
    return sqlite_result or supabase_result

# Helper functions for common database operations

def get_user_by_username(username):
    """Get a user by username"""
    with get_supabase_session() as supabase:
        response = supabase.table("users").select("*").eq("username", username).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None

def get_user_by_id(user_id):
    """Get a user by ID"""
    with get_supabase_session() as supabase:
        response = supabase.table("users").select("*").eq("id", user_id).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None

def create_user(user_data):
    """Create a new user"""
    with get_supabase_session(use_service_key=True) as supabase:
        response = supabase.table("users").insert(user_data).execute()
        return response.data[0] if response.data else None

def update_user(user_id, user_data):
    """Update a user"""
    with get_supabase_session(use_service_key=True) as supabase:
        response = supabase.table("users").update(user_data).eq("id", user_id).execute()
        return response.data[0] if response.data else None

def delete_user(user_id):
    """Delete a user"""
    with get_supabase_session(use_service_key=True) as supabase:
        response = supabase.table("users").delete().eq("id", user_id).execute()
        return response.data[0] if response.data else None