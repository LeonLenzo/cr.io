import streamlit as st
import os
from functools import wraps
from datetime import datetime
from user_model_supabase import User
from db_utils_supabase import get_supabase_session

def login_user():
    """Display login form and authenticate user"""
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    
    if st.session_state.user_id is not None:
        return True
    
    with st.form("login_form"):
        st.subheader("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            # Get user from Supabase
            user = User.get_by_username(username)
            
            if user and user.check_password(password):
                if user.is_active:
                    st.session_state.user_id = user.id
                    st.session_state.user_role = user.role
                    st.session_state.username = user.username
                    
                    # Update last login time
                    user.update_last_login()
                    
                    st.success(f"Welcome, {user.username}!")
                    st.rerun()
                else:
                    st.error("Your account is inactive. Please contact an administrator.")
            else:
                st.error("Invalid username or password")
    
    return False

def logout_user():
    """Log out the current user"""
    if "user_id" in st.session_state:
        st.session_state.user_id = None
        st.session_state.user_role = None
        st.session_state.username = None
        st.success("Logged out successfully")
        st.rerun()

def verify_admin_password(operation_name="this operation"):
    """Verify admin password before performing destructive operations"""
    if "user_role" not in st.session_state or st.session_state.user_role != "admin":
        st.error("You must be an admin to perform this operation")
        return False
    
    with st.form(f"password_verify_{operation_name}"):
        st.warning(f"⚠️ You're about to {operation_name}. This action cannot be undone.")
        password = st.text_input("Enter your password to confirm:", type="password")
        submit = st.form_submit_button("Verify")
        
        if submit:
            user = User.get_by_id(st.session_state.user_id)
            if user and user.check_password(password):
                st.success("Password verified")
                return True
            else:
                st.error("Incorrect password")
    
    return False

def require_login(func):
    """Decorator to require user login before executing a function"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user_id" not in st.session_state or st.session_state.user_id is None:
            st.warning("Please log in to access this feature")
            login_user()
            return None
        return func(*args, **kwargs)
    return wrapper

def require_admin(func):
    """Decorator to require admin authentication before executing a function"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user_id" not in st.session_state or st.session_state.user_id is None:
            st.warning("Please log in to access this feature")
            login_user()
            return None
            
        if "user_role" not in st.session_state or st.session_state.user_role != "admin":
            st.error("You must be an admin to access this feature")
            return None
            
        return func(*args, **kwargs)
    return wrapper

def require_role(role):
    """Decorator factory to require a specific role before executing a function"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if "user_id" not in st.session_state or st.session_state.user_id is None:
                st.warning("Please log in to access this feature")
                login_user()
                return None
                
            if "user_role" not in st.session_state or st.session_state.user_role not in role:
                st.error(f"You must have one of these roles to access this feature: {', '.join(role)}")
                return None
                
            return func(*args, **kwargs)
        return wrapper
    return decorator

def display_user_info():
    """Display current user information and logout button"""
    if "user_id" in st.session_state and st.session_state.user_id is not None:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"Logged in as: **{st.session_state.username}** ({st.session_state.user_role})")
        with col2:
            if st.button("Logout"):
                logout_user()

# Rate limiting for login attempts
login_attempts = {}

def check_rate_limit(username, ip_address="unknown"):
    """Check if login attempts should be rate limited"""
    current_time = datetime.utcnow()
    
    # Create a unique key for this username/IP combination
    key = f"{username}:{ip_address}"
    
    if key in login_attempts:
        attempts, last_attempt_time = login_attempts[key]
        
        # If too many recent attempts, enforce a cooldown
        time_diff = (current_time - last_attempt_time).total_seconds()
        if attempts >= 5 and time_diff < 900:  # 15 minutes (900 seconds)
            remaining = 15 - time_diff / 60
            return False, f"Too many login attempts. Please try again in {remaining:.1f} minutes."
        
        # Reset attempts if cooldown period has passed
        if time_diff > 900:
            login_attempts[key] = (1, current_time)
        else:
            login_attempts[key] = (attempts + 1, current_time)
    else:
        # First attempt
        login_attempts[key] = (1, current_time)
    
    return True, None

def reset_rate_limit(username, ip_address="unknown"):
    """Reset rate limit for a user after successful login"""
    key = f"{username}:{ip_address}"
    if key in login_attempts:
        del login_attempts[key]