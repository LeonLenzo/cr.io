# This file is now a wrapper around db_utils.py to maintain backward compatibility
import os
from db_utils import init_db, get_db_session, backup_database

# Import models to ensure they're registered with Base
from model import Freezer, Rack, Box, Sample
from user_model import User
from sample_history import SampleHistory

# --- Usage Example ---
if __name__ == "__main__":
    # Create backup directory
    if not os.path.exists("backups"):
        os.makedirs("backups")
    
    # Initialize database
    with get_db_session() as session:
        print("Database initialized with all tables.")
    
    # Create a backup
    backup_database()