import os
import hashlib
import bcrypt
from datetime import datetime
from db_utils import get_supabase_session, get_user_by_username, create_user, update_user, delete_user

class User:
    """User model for Supabase"""
    
    def __init__(self, data=None):
        """Initialize a user from Supabase data"""
        if data:
            self.id = data.get('id')
            self.username = data.get('username')
            self.email = data.get('email')
            self.password_hash = data.get('password_hash')
            self.salt = data.get('salt')
            self.role = data.get('role', 'user')
            self.created_at = data.get('created_at')
            self.last_login = data.get('last_login')
            self.is_active = data.get('is_active', True)
        else:
            self.id = None
            self.username = None
            self.email = None
            self.password_hash = None
            self.salt = None
            self.role = 'user'
            self.created_at = datetime.utcnow().isoformat()
            self.last_login = None
            self.is_active = True
    
    def to_dict(self):
        """Convert user to dictionary for Supabase"""
        return {
            'username': self.username,
            'email': self.email,
            'password_hash': self.password_hash,
            'salt': self.salt,
            'role': self.role,
            'created_at': self.created_at,
            'last_login': self.last_login,
            'is_active': self.is_active
        }
    
    @staticmethod
    def hash_password(password, salt=None):
        """Hash a password with bcrypt"""
        if salt is None:
            # Generate a salt with bcrypt
            salt = bcrypt.gensalt().decode('utf-8')
        else:
            # Ensure salt is bytes for bcrypt
            if isinstance(salt, str):
                salt = salt.encode('utf-8')
        
        # Hash the password with the salt
        if isinstance(password, str):
            password = password.encode('utf-8')
            
        password_hash = bcrypt.hashpw(password, salt if isinstance(salt, bytes) else salt.encode('utf-8'))
        
        return password_hash.decode('utf-8'), salt.decode('utf-8') if isinstance(salt, bytes) else salt
    
    @staticmethod
    def verify_password(password, password_hash, salt):
        """Verify a password against a hash"""
        if isinstance(password, str):
            password = password.encode('utf-8')
        if isinstance(password_hash, str):
            password_hash = password_hash.encode('utf-8')
        if isinstance(salt, str):
            salt = salt.encode('utf-8')
            
        # For bcrypt, the salt is included in the hash
        return bcrypt.checkpw(password, password_hash)
    
    def set_password(self, password):
        """Set the password for this user"""
        self.password_hash, self.salt = User.hash_password(password)
    
    def check_password(self, password):
        """Check if the provided password is correct"""
        return User.verify_password(password, self.password_hash, self.salt)
    
    @staticmethod
    def get_by_username(username):
        """Get a user by username"""
        user_data = get_user_by_username(username)
        return User(user_data) if user_data else None
    
    @staticmethod
    def get_by_id(user_id):
        """Get a user by ID"""
        with get_supabase_session() as supabase:
            response = supabase.table("users").select("*").eq("id", user_id).execute()
            if response.data and len(response.data) > 0:
                return User(response.data[0])
            return None
    
    def save(self):
        """Save or update the user in Supabase"""
        user_dict = self.to_dict()
        
        if self.id:
            # Update existing user
            with get_supabase_session(use_service_key=True) as supabase:
                response = supabase.table("users").update(user_dict).eq("id", self.id).execute()
                if response.data and len(response.data) > 0:
                    self.id = response.data[0]['id']
                    return True
        else:
            # Create new user
            with get_supabase_session(use_service_key=True) as supabase:
                response = supabase.table("users").insert(user_dict).execute()
                if response.data and len(response.data) > 0:
                    self.id = response.data[0]['id']
                    return True
        
        return False
    
    def delete(self):
        """Delete the user from Supabase"""
        if not self.id:
            return False
            
        with get_supabase_session(use_service_key=True) as supabase:
            response = supabase.table("users").delete().eq("id", self.id).execute()
            return len(response.data) > 0
    
    @staticmethod
    def get_all_users():
        """Get all users"""
        with get_supabase_session(use_service_key=True) as supabase:
            response = supabase.table("users").select("*").execute()
            return [User(user_data) for user_data in response.data]
    
    def update_last_login(self):
        """Update the last login time"""
        self.last_login = datetime.utcnow().isoformat()
        with get_supabase_session(use_service_key=True) as supabase:
            supabase.table("users").update({"last_login": self.last_login}).eq("id", self.id).execute()