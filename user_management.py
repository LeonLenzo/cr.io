import streamlit as st
import pandas as pd
from datetime import datetime
from user_model_supabase import User
from auth_supabase import require_admin, require_login

def display_user_management():
    """Display user management interface for admins"""
    if "user_role" in st.session_state and st.session_state.user_role == "admin":
        tabs = st.tabs(["User List", "Add User", "User Roles"])
        
        with tabs[0]:
            display_user_list()
        
        with tabs[1]:
            display_add_user_form()
        
        with tabs[2]:
            display_user_roles_management()
    
    # Display user profile for all logged-in users
    if "user_id" in st.session_state and st.session_state.user_id is not None:
        st.subheader("My Profile")
        display_user_profile()

@require_admin
def display_user_list():
    """Display a list of all users (admin only)"""
    users = User.get_all_users()
    
    if not users:
        st.warning("No users found in the system.")
        return
    
    # Convert to DataFrame for display
    user_data = []
    for user in users:
        # Parse ISO format dates if they're strings
        created_at = user.created_at
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except:
                created_at = None
                
        last_login = user.last_login
        if isinstance(last_login, str):
            try:
                last_login = datetime.fromisoformat(last_login.replace('Z', '+00:00'))
            except:
                last_login = None
        
        user_data.append({
            "ID": user.id,
            "Username": user.username,
            "Email": user.email,
            "Role": user.role,
            "Created": created_at.strftime("%Y-%m-%d") if created_at else "",
            "Last Login": last_login.strftime("%Y-%m-%d %H:%M") if last_login else "Never",
            "Status": "Active" if user.is_active else "Inactive"
        })
    
    df = pd.DataFrame(user_data)
    st.dataframe(df)
    
    # User actions
    st.subheader("User Actions")
    col1, col2 = st.columns(2)
    
    with col1:
        user_to_edit = st.selectbox(
            "Select User",
            options=[user.username for user in users],
            format_func=lambda x: x
        )
        
    with col2:
        action = st.selectbox(
            "Action",
            options=["Change Role", "Reset Password", "Activate/Deactivate", "Delete User"]
        )
    
    if st.button("Perform Action"):
        selected_user = next((u for u in users if u.username == user_to_edit), None)
        if not selected_user:
            st.error("User not found")
            return
            
        if action == "Change Role":
            change_user_role(selected_user.id)
        elif action == "Reset Password":
            reset_user_password(selected_user.id)
        elif action == "Activate/Deactivate":
            toggle_user_status(selected_user.id)
        elif action == "Delete User":
            delete_user(selected_user.id)

@require_admin
def display_add_user_form():
    """Display form to add a new user (admin only)"""
    with st.form("add_user_form"):
        st.subheader("Add New User")
        
        username = st.text_input("Username", help="Username must be unique")
        email = st.text_input("Email", help="Email must be unique")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        role = st.selectbox("Role", options=["user", "admin", "readonly"])
        
        submitted = st.form_submit_button("Add User")
        
        if submitted:
            if not username or not email or not password:
                st.error("All fields are required")
                return
                
            if password != confirm_password:
                st.error("Passwords do not match")
                return
                
            # Check if username or email already exists
            existing_user = User.get_by_username(username)
            if existing_user:
                st.error(f"Username '{username}' is already taken")
                return
            
            # Create new user
            new_user = User()
            new_user.username = username
            new_user.email = email
            new_user.role = role
            new_user.created_at = datetime.utcnow().isoformat()
            new_user.is_active = True
            new_user.set_password(password)
            
            if new_user.save():
                st.success(f"User '{username}' added successfully")
                st.rerun()
            else:
                st.error("Failed to create user")

@require_admin
def display_user_roles_management():
    """Display interface to manage user roles (admin only)"""
    st.subheader("User Roles")
    
    st.markdown("""
    **Available Roles:**
    - **Admin**: Full access to all features, including user management
    - **User**: Can add, edit, and view samples, but cannot manage users
    - **ReadOnly**: Can only view samples, cannot make changes
    """)
    
    st.markdown("---")
    
    users = User.get_all_users()
    
    if not users:
        st.warning("No users found in the system.")
        return
    
    # Create a form for batch role updates
    with st.form("batch_role_update"):
        st.subheader("Batch Role Update")
        
        # Create a dictionary to store role selections
        role_selections = {}
        
        for user in users:
            role_selections[user.id] = st.selectbox(
                f"Role for {user.username}",
                options=["user", "admin", "readonly"],
                index=["user", "admin", "readonly"].index(user.role)
            )
        
        submitted = st.form_submit_button("Update Roles")
        
        if submitted:
            changes_made = False
            
            for user_id, new_role in role_selections.items():
                user = User.get_by_id(user_id)
                if user and user.role != new_role:
                    user.role = new_role
                    if user.save():
                        changes_made = True
            
            if changes_made:
                st.success("User roles updated successfully")
                st.rerun()
            else:
                st.info("No role changes were made")

@require_login
def display_user_profile():
    """Display and allow editing of the current user's profile"""
    current_user = User.get_by_id(st.session_state.user_id)
    
    if not current_user:
        st.error("User not found")
        return
    
    st.subheader("My Profile")
    
    # Display user info
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Username:** {current_user.username}")
        st.write(f"**Email:** {current_user.email}")
    with col2:
        st.write(f"**Role:** {current_user.role}")
        
        # Parse created_at if it's a string
        created_at = current_user.created_at
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                created_at_str = created_at.strftime('%Y-%m-%d')
            except:
                created_at_str = "Unknown"
        else:
            created_at_str = created_at.strftime('%Y-%m-%d') if created_at else "Unknown"
            
        st.write(f"**Account Created:** {created_at_str}")
    
    # Change password form
    with st.form("change_password_form"):
        st.subheader("Change Password")
        
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        submitted = st.form_submit_button("Change Password")
        
        if submitted:
            if not current_password or not new_password or not confirm_password:
                st.error("All fields are required")
                return
                
            if new_password != confirm_password:
                st.error("New passwords do not match")
                return
                
            if not current_user.check_password(current_password):
                st.error("Current password is incorrect")
                return
                
            current_user.set_password(new_password)
            if current_user.save():
                st.success("Password changed successfully")
            else:
                st.error("Failed to update password")

def change_user_role(user_id):
    """Change a user's role"""
    user = User.get_by_id(user_id)
    
    if not user:
        st.error("User not found")
        return
    
    # Create a form for role change
    with st.form("change_role_form"):
        st.subheader(f"Change Role for {user.username}")
        
        new_role = st.selectbox(
            "New Role",
            options=["user", "admin", "readonly"],
            index=["user", "admin", "readonly"].index(user.role)
        )
        
        submitted = st.form_submit_button("Update Role")
        
        if submitted:
            user.role = new_role
            if user.save():
                st.success(f"Role for {user.username} updated to {new_role}")
                st.rerun()
            else:
                st.error("Failed to update user role")

def reset_user_password(user_id):
    """Reset a user's password"""
    user = User.get_by_id(user_id)
    
    if not user:
        st.error("User not found")
        return
    
    # Create a form for password reset
    with st.form("reset_password_form"):
        st.subheader(f"Reset Password for {user.username}")
        
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        submitted = st.form_submit_button("Reset Password")
        
        if submitted:
            if not new_password:
                st.error("Password is required")
                return
                
            if new_password != confirm_password:
                st.error("Passwords do not match")
                return
                
            user.set_password(new_password)
            if user.save():
                st.success(f"Password for {user.username} has been reset")
                st.rerun()
            else:
                st.error("Failed to reset password")

def toggle_user_status(user_id):
    """Activate or deactivate a user"""
    user = User.get_by_id(user_id)
    
    if not user:
        st.error("User not found")
        return
    
    # Create a confirmation form
    with st.form("toggle_status_form"):
        current_status = "active" if user.is_active else "inactive"
        new_status = "inactive" if user.is_active else "active"
        
        st.subheader(f"{'Deactivate' if user.is_active else 'Activate'} User: {user.username}")
        st.write(f"Current status: **{current_status}**")
        st.write(f"New status: **{new_status}**")
        
        submitted = st.form_submit_button(f"{'Deactivate' if user.is_active else 'Activate'} User")
        
        if submitted:
            user.is_active = not user.is_active
            if user.save():
                st.success(f"User {user.username} is now {new_status}")
                st.rerun()
            else:
                st.error(f"Failed to update user status")

def delete_user(user_id):
    """Delete a user"""
    user = User.get_by_id(user_id)
    
    if not user:
        st.error("User not found")
        return
    
    # Create a confirmation form
    with st.form("delete_user_form"):
        st.subheader(f"Delete User: {user.username}")
        st.warning("⚠️ This action cannot be undone. All data associated with this user will be permanently deleted.")
        
        confirmation = st.text_input("Type the username to confirm deletion")
        
        submitted = st.form_submit_button("Delete User")
        
        if submitted:
            if confirmation != user.username:
                st.error("Username confirmation does not match")
                return
            
            if user.delete():
                st.success(f"User {user.username} has been deleted")
                st.rerun()
            else:
                st.error("Failed to delete user")

def create_initial_admin():
    """Create an initial admin user if no users exist"""
    # Check if any users exist
    users = User.get_all_users()
    
    if not users:
        # Get admin password from environment or secrets
        admin_password = None
        
        # Try to get from Streamlit secrets first
        if hasattr(st, "secrets") and "admin" in st.secrets:
            admin_password = st.secrets.get("admin", {}).get("initial_password")
        
        # Fall back to environment variable
        if not admin_password:
            admin_password = os.environ.get("ADMIN_INITIAL_PASSWORD", "admin123")
        
        # Create default admin user
        admin_user = User()
        admin_user.username = "admin"
        admin_user.email = "admin@example.com"
        admin_user.role = "admin"
        admin_user.created_at = datetime.utcnow().isoformat()
        admin_user.is_active = True
        admin_user.set_password(admin_password)
        
        if admin_user.save():
            print(f"Created initial admin user: admin / {admin_password}")
            return True
    
    return False