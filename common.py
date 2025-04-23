import streamlit as st
from db_utils import get_db_session

def verify_admin_password(operation_name="this operation", password_key="admin_pw"):
    """Verify admin password before performing destructive operations"""
    password_correct = False
    
    with st.form(f"password_verify_{operation_name}"):
        st.warning(f"⚠️ You're about to {operation_name}. This action cannot be undone.")
        password = st.text_input("Enter admin password:", type="password")
        submit = st.form_submit_button("Verify")
        
        if submit:
            # Change this to your desired admin password
            # In a production environment, this should use environment variables
            # and proper password hashing
            if password == "admin123":
                password_correct = True
                st.success("Password verified")
            else:
                st.error("Incorrect password")
    
    return password_correct

def handle_delete_confirmation(item_type, item_id, delete_function, additional_params=None):
    """
    Generic function to handle delete confirmations with password protection
    
    Parameters:
    - item_type: Type of item being deleted (freezer, rack, box, sample)
    - item_id: ID of the item to delete
    - delete_function: Function to call if deletion is confirmed
    - additional_params: Additional parameters needed for deletion
    """
    if additional_params is None:
        additional_params = {}
    
    # Set up session state for deletion confirmation
    if "delete_confirmation" not in st.session_state:
        st.session_state.delete_confirmation = False
    if "delete_target" not in st.session_state:
        st.session_state.delete_target = None
    if "delete_type" not in st.session_state:
        st.session_state.delete_type = None
    
    # Request confirmation
    if st.button(f"Delete {item_type.title()}"):
        st.session_state.delete_confirmation = True
        st.session_state.delete_target = item_id
        st.session_state.delete_type = item_type
        st.rerun()
    
    # Check if we're confirming deletion for this item
    if (st.session_state.delete_confirmation and 
            st.session_state.delete_type == item_type and 
            st.session_state.delete_target == item_id):
        
        st.warning(f"⚠️ You're about to delete {item_type} '{item_id}'. This action cannot be undone.")
        
        # Password form
        password = st.text_input("Enter admin password:", type="password", key=f"{item_type}_pw")
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("Confirm Delete"):
                # Change this to your desired admin password
                if password == "admin123":
                    with get_db_session() as session:
                        success = delete_function(session, item_id, **additional_params)
                        if success:
                            st.success(f"Deleted {item_type} '{item_id}'")
                            # Reset session state
                            st.session_state.delete_confirmation = False
                            st.session_state.delete_target = None
                            st.session_state.delete_type = None
                            return True
                else:
                    st.error("Incorrect password")
        with col2:
            if st.button("Cancel"):
                st.session_state.delete_confirmation = False
                st.session_state.delete_target = None
                st.session_state.delete_type = None
                st.rerun()
    
    return False