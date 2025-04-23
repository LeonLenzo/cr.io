import streamlit as st
from db_utils import get_db_session
from model import Rack
from common import handle_delete_confirmation

def display_rack_selection():
    """Display the rack selection interface if a freezer is selected"""
    if not st.session_state.selected_freezer:
        return
    
    with get_db_session() as session:
        rack_expanded = st.session_state.selected_rack is None
        with st.expander("2⃣ Select Rack" if rack_expanded else f"✅ Rack: {st.session_state.selected_rack}", expanded=rack_expanded):
            display_rack_list(session)
            add_new_rack(session)
            
            if st.session_state.selected_rack:
                handle_rack_deletion(st.session_state.selected_rack)

def display_rack_list(session):
    """Display the list of racks in the selected freezer as buttons"""
    racks = session.query(Rack).filter_by(freezer_name=st.session_state.selected_freezer).order_by(Rack.id).all()
    if not racks:
        st.warning("No racks in this freezer.")
    else:
        for rack in racks:
            if st.button(f"📦 {rack.id} ({rack.rows}x{rack.columns})", key=f"btn_rack_{rack.id}"):
                st.session_state.selected_rack = rack.id
                st.session_state.selected_box = None
                st.session_state.selected_well = None
                st.rerun()

def add_new_rack(session):
    """Display form to add a new rack"""
    with st.form("add_rack_form"):
        st.markdown("➕ Add New Rack")
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        with col1:
            rack_id = st.text_input("Rack ID")
        with col2:
            rows = st.number_input("Rows", min_value=1, max_value=20, value=5)
        with col3:
            cols = st.number_input("Cols", min_value=1, max_value=20, value=6)
        with col4:
            st.markdown("<br>", unsafe_allow_html=True)
            submit = st.form_submit_button("Add Rack")

        if submit and rack_id:
            existing = session.query(Rack).filter_by(id=rack_id.strip(), freezer_name=st.session_state.selected_freezer).first()
            if not existing:
                session.add(Rack(id=rack_id.strip(), freezer_name=st.session_state.selected_freezer, rows=rows, columns=cols))
                session.commit()
                st.success(f"Added rack '{rack_id.strip()}'")
                st.rerun()
            else:
                st.error(f"Rack '{rack_id.strip()}' already exists in this freezer")

def handle_rack_deletion(rack_id):
    """Handle the deletion of a rack with confirmation"""
    def delete_rack(session, rack_id, **kwargs):
        """Delete a rack from the database"""
        rack_to_delete = session.query(Rack).filter_by(
            id=rack_id, 
            freezer_name=st.session_state.selected_freezer
        ).first()
        if rack_to_delete:
            session.delete(rack_to_delete)
            session.commit()
            # Reset session state
            st.session_state.selected_rack = None
            st.session_state.selected_box = None
            st.session_state.selected_well = None
            return True
        return False
    
    # Use the common delete confirmation handler
    additional_params = {"freezer_name": st.session_state.selected_freezer}
    if handle_delete_confirmation("rack", rack_id, delete_rack, additional_params):
        st.rerun()