import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from model import Base, Sample
from auth import require_login
from db_utils import get_db_session

class SampleHistory(Base):
    __tablename__ = "sample_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sample_id = Column(Integer, ForeignKey("samples.id", ondelete="CASCADE"))
    action = Column(String, nullable=False)  # created, updated, deleted
    field = Column(String)  # Which field was changed (null for created/deleted)
    old_value = Column(Text)  # Old value (null for created)
    new_value = Column(Text)  # New value (null for deleted)
    user_id = Column(Integer)  # User who made the change
    username = Column(String)  # Username cached for display
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Additional fields to help with filtering and display
    freezer = Column(String)
    rack = Column(String)
    box = Column(String)
    well = Column(String)
    sample_name = Column(String)

def log_sample_action(sample, action, field=None, old_value=None, new_value=None):
    """
    Log a sample action to the history table
    
    Parameters:
    - sample: The Sample object
    - action: The action performed (created, updated, deleted)
    - field: The field that was changed (for updates)
    - old_value: The previous value (for updates)
    - new_value: The new value (for updates)
    """
    if "user_id" not in st.session_state or st.session_state.user_id is None:
        user_id = 0
        username = "System"
    else:
        user_id = st.session_state.user_id
        username = st.session_state.username
    
    with get_db_session() as session:
        history_entry = SampleHistory(
            sample_id=sample.id,
            action=action,
            field=field,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
            user_id=user_id,
            username=username,
            freezer=sample.freezer,
            rack=sample.rack,
            box=sample.box,
            well=sample.well,
            sample_name=sample.sample_name
        )
        session.add(history_entry)
        session.commit()

def log_sample_creation(sample):
    """Log the creation of a new sample"""
    log_sample_action(sample, "created")

def log_sample_update(sample, field, old_value, new_value):
    """Log an update to a sample field"""
    log_sample_action(sample, "updated", field, old_value, new_value)

def log_sample_deletion(sample):
    """Log the deletion of a sample"""
    log_sample_action(sample, "deleted")

def log_bulk_sample_changes(added, updated, deleted):
    """
    Log bulk changes to samples
    
    Parameters:
    - added: List of new Sample objects
    - updated: List of (sample, field, old_value, new_value) tuples
    - deleted: List of deleted Sample objects
    """
    for sample in added:
        log_sample_creation(sample)
    
    for sample, field, old_value, new_value in updated:
        log_sample_update(sample, field, old_value, new_value)
    
    for sample in deleted:
        log_sample_deletion(sample)

@require_login
def display_sample_history():
    """Display the sample history interface"""
    # Check if the sample_history table exists
    try:
        with get_db_session() as session:
            # Try to query the table to see if it exists
            session.query(SampleHistory).limit(1).all()
            
            # If we get here, the table exists
            display_sample_history_content()
    except Exception as e:
        # Table doesn't exist or other error
        st.warning("Sample history tracking is not available yet. Please initialize the database first.")
        st.info("Run `python init_db.py` to create all required tables.")
        if st.button("Initialize Database"):
            try:
                import subprocess
                result = subprocess.run(["python3", "init_db.py"], capture_output=True, text=True)
                if result.returncode == 0:
                    st.success("Database initialized successfully. Please refresh the page.")
                else:
                    st.error(f"Error initializing database: {result.stderr}")
            except Exception as e:
                st.error(f"Error running initialization: {str(e)}")

def display_sample_history_content():
    """Display the sample history interface content"""
    # Filters
    st.subheader("Filter History")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filter_action = st.multiselect(
            "Action",
            options=["created", "updated", "deleted"],
            default=["created", "updated", "deleted"]
        )
    
    with col2:
        with get_db_session() as session:
            try:
                all_users = session.query(SampleHistory.username).distinct().all()
                user_options = [u[0] for u in all_users]
            except:
                user_options = []
            
            filter_user = st.multiselect(
                "User",
                options=user_options,
                default=[]
            )
    
    with col3:
        date_range = st.date_input(
            "Date Range",
            value=(datetime.now().date(), datetime.now().date()),
            help="Filter by date range"
        )
    
    # Sample-specific filters
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        filter_freezer = st.text_input("Freezer", help="Filter by freezer name")
    with col2:
        filter_rack = st.text_input("Rack", help="Filter by rack ID")
    with col3:
        filter_box = st.text_input("Box", help="Filter by box ID")
    with col4:
        filter_sample = st.text_input("Sample Name", help="Filter by sample name")
    
    # Apply filters and display results
    if st.button("Apply Filters"):
        display_filtered_history(
            filter_action, filter_user, date_range,
            filter_freezer, filter_rack, filter_box, filter_sample
        )

def display_filtered_history(filter_action, filter_user, date_range, 
                            filter_freezer, filter_rack, filter_box, filter_sample):
    """Display filtered sample history"""
    try:
        with get_db_session() as session:
            # Start with base query
            query = session.query(SampleHistory)
            
            # Apply filters
            if filter_action:
                query = query.filter(SampleHistory.action.in_(filter_action))
            
            if filter_user:
                query = query.filter(SampleHistory.username.in_(filter_user))
            
            if len(date_range) == 2:
                start_date, end_date = date_range
                start_datetime = datetime.combine(start_date, datetime.min.time())
                end_datetime = datetime.combine(end_date, datetime.max.time())
                query = query.filter(SampleHistory.timestamp.between(start_datetime, end_datetime))
            
            if filter_freezer:
                query = query.filter(SampleHistory.freezer.like(f"%{filter_freezer}%"))
            
            if filter_rack:
                query = query.filter(SampleHistory.rack.like(f"%{filter_rack}%"))
            
            if filter_box:
                query = query.filter(SampleHistory.box.like(f"%{filter_box}%"))
            
            if filter_sample:
                query = query.filter(SampleHistory.sample_name.like(f"%{filter_sample}%"))
            
            # Order by timestamp (newest first)
            query = query.order_by(SampleHistory.timestamp.desc())
            
            # Execute query
            history_entries = query.all()
            
            # Check if we have any results
            if not history_entries:
                st.info("No history entries found matching the filters.")
                return
            
            # Convert to DataFrame for display
            data = []
            for entry in history_entries:
                action_display = {
                    "created": "✅ Created",
                    "updated": "🔄 Updated",
                    "deleted": "❌ Deleted"
                }.get(entry.action, entry.action)
                
                # Format the change description
                if entry.action == "updated":
                    change = f"Changed {entry.field} from '{entry.old_value}' to '{entry.new_value}'"
                elif entry.action == "created":
                    change = "New sample created"
                else:  # deleted
                    change = "Sample deleted"
                
                data.append({
                    "Date": entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "User": entry.username,
                    "Action": action_display,
                    "Sample": entry.sample_name,
                    "Location": f"{entry.freezer}/{entry.rack}/{entry.box}/{entry.well}",
                    "Change": change
                })
            
            df = pd.DataFrame(data)
            
            # Display results
            st.subheader(f"History Results ({len(history_entries)} entries)")
            st.dataframe(df, use_container_width=True)
            
            # Add download button
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Download History",
                csv,
                "sample_history.csv",
                "text/csv",
                key='download-history'
            )
    except Exception as e:
        st.warning("Unable to display sample history. The history tracking system may not be fully initialized.")
        st.info("Run `python init_db.py` to create all required tables.")

def display_sample_audit_trail(sample):
    """Display the audit trail for a specific sample"""
    try:
        with get_db_session() as session:
            history_entries = session.query(SampleHistory).filter_by(
                sample_id=sample.id
            ).order_by(SampleHistory.timestamp.desc()).all()
            
            if not history_entries:
                st.info("No history available for this sample.")
                return
            
            st.subheader(f"Audit Trail for {sample.sample_name}")
            
            # Convert to DataFrame for display
            data = []
            for entry in history_entries:
                action_display = {
                    "created": "✅ Created",
                    "updated": "🔄 Updated",
                    "deleted": "❌ Deleted"
                }.get(entry.action, entry.action)
                
                # Format the change description
                if entry.action == "updated":
                    change = f"Changed {entry.field} from '{entry.old_value}' to '{entry.new_value}'"
                elif entry.action == "created":
                    change = "Sample created"
                else:  # deleted
                    change = "Sample deleted"
                
                data.append({
                    "Date": entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "User": entry.username,
                    "Action": action_display,
                    "Change": change
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.warning("Unable to display sample history. The history tracking system may not be fully initialized.")
        st.info("Run `python init_db.py` to create all required tables.")