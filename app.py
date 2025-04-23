# cr.io - Laboratory Information Management System (Supabase Version)
import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Supabase modules
from db_utils_supabase import get_supabase_session, init_supabase_tables
from user_model_supabase import User
from auth_supabase import login_user, display_user_info
from user_management_supabase import display_user_management, create_initial_admin

# Import other modular components
# Note: These would need to be updated to use Supabase as well
from search import display_search_interface
from freezer import display_freezer_selection
from rack import display_rack_selection
from box import display_box_selection
from sample import display_sample_management
from sample_history import display_sample_history, display_sample_history_content
from data_visualization import display_data_visualization, display_sample_overview
from data_visualization import display_storage_utilization, display_sample_timeline, display_custom_analysis

# --- Streamlit Layout ---
st.set_page_config(
    page_title="cr.io",
    page_icon="❄️",
    layout="wide")
st.markdown("<h1 style='text-align: center;'>❄️ cr.io ❄️</h1>", unsafe_allow_html=True)
st.markdown("---")

# --- Initialize Database ---
def ensure_database_initialized():
    """Ensure that the database is initialized with all required tables"""
    try:
        # Initialize Supabase tables
        if init_supabase_tables():
            # Create initial admin user if needed
            create_initial_admin()
            return True
        else:
            return False
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False

# --- Initialize Session State ---
def initialize_session_state():
    """Initialize all session state variables"""
    # Navigation state
    for key in ["selected_freezer", "selected_rack", "selected_box", "selected_well"]:
        if key not in st.session_state:
            st.session_state[key] = None
    
    # Box form position
    if "box_form_position" not in st.session_state:
        st.session_state.box_form_position = None
    
    # Delete confirmation state
    if "delete_confirmation" not in st.session_state:
        st.session_state.delete_confirmation = False
    if "delete_target" not in st.session_state:
        st.session_state.delete_target = None
    if "delete_type" not in st.session_state:
        st.session_state.delete_type = None
    
    # User state
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "user_role" not in st.session_state:
        st.session_state.user_role = None
    if "username" not in st.session_state:
        st.session_state.username = None
    
    # Database initialization state
    if "database_initialized" not in st.session_state:
        st.session_state.database_initialized = ensure_database_initialized()

# Initialize session state
initialize_session_state()

# --- Main Application ---
def main():
    """Main application function"""
    # Check if database is initialized
    if not st.session_state.database_initialized:
        st.error("Database connection to Supabase failed. Please check your credentials.")
        
        # Show configuration status
        st.subheader("Configuration Status")
        
        # Check for environment variables
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            st.warning("Supabase credentials not found in environment variables.")
            st.info("Please create a .env file with your Supabase credentials.")
            
            with st.expander("Environment Setup Instructions"):
                st.code("""
                # Create a .env file with the following content:
                SUPABASE_URL=https://your-project-url.supabase.co
                SUPABASE_KEY=your-supabase-anon-key
                SUPABASE_SERVICE_KEY=your-supabase-service-role-key
                """)
        else:
            st.success("Supabase credentials found in environment variables.")
            st.warning("However, connection to Supabase failed. Please check if the credentials are correct.")
        
        if st.button("Retry Connection"):
            if ensure_database_initialized():
                st.session_state.database_initialized = True
                st.success("Connected to Supabase successfully!")
                st.rerun()
            else:
                st.error("Failed to connect to Supabase. Please check your credentials.")
        
        return
    
    # Display user info and login/logout in the sidebar
    display_user_info()
    
    # Check if user is logged in
    is_logged_in = "user_id" in st.session_state and st.session_state.user_id is not None
    
    if not is_logged_in:
        # Display login form
        login_user()
    else:
        # Create sidebar tabs
        sidebar_tabs = ["Sample Management", "Data Visualization", "Sample History"]
        
        # Add User Management tab for admins
        if "user_role" in st.session_state and st.session_state.user_role == "admin":
            sidebar_tabs.append("User Management")
        
        selected_tab = st.sidebar.radio("Navigate", sidebar_tabs)
        
        # Display content based on selected tab
        if selected_tab == "Sample Management":
            st.markdown("## Sample Management")
            
            # Display search interface
            display_search_interface()
            
            # Display hierarchical navigation
            display_freezer_selection()
            display_rack_selection()
            display_box_selection()
            display_sample_management()
            
        elif selected_tab == "Data Visualization":
            st.markdown("## Data Visualization")
            
            # Try to display data visualization
            try:
                # Instead of using an expander, display directly
                tabs = st.tabs(["Sample Overview", "Storage Utilization", "Sample Timeline", "Custom Analysis"])
                
                with tabs[0]:
                    display_sample_overview()
                
                with tabs[1]:
                    display_storage_utilization()
                
                with tabs[2]:
                    display_sample_timeline()
                
                with tabs[3]:
                    display_custom_analysis()
                    
            except Exception as e:
                st.warning(f"Data visualization is not available. Error: {str(e)}")
                st.info("Make sure your Supabase tables are properly set up.")
                
        elif selected_tab == "Sample History":
            st.markdown("## Sample History")
            
            # Try to display sample history
            try:
                # Check if we can access the sample_history table
                with get_supabase_session() as supabase:
                    response = supabase.table("sample_history").select("count", count="exact").limit(1).execute()
                    
                    # If we get here, the table exists
                    display_sample_history_content()
            except Exception as e:
                st.warning(f"Sample history is not available. Error: {str(e)}")
                st.info("Make sure your Supabase tables are properly set up.")
                
        elif selected_tab == "User Management":
            st.markdown("## User Management")
            
            # Display user management interface
            display_user_management()

if __name__ == "__main__":
    main()