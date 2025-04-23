import streamlit as st
from db_utils import get_db_session
from model import Freezer
from common import handle_delete_confirmation

def display_freezer_selection():
    """Display the freezer selection interface"""
    with get_db_session() as session:
        freezer_expanded = st.session_state.selected_freezer is None
        with st.expander("1⃣ Select Freezer" if freezer_expanded else f"✅ Freezer: {st.session_state.selected_freezer}", expanded=freezer_expanded):
            display_freezer_list(session)
            add_new_freezer(session)
            
            if st.session_state.selected_freezer:
                handle_freezer_deletion(st.session_state.selected_freezer)

def display_freezer_list(session):
    """Display the list of freezers as buttons"""
    freezers = session.query(Freezer).order_by(Freezer.name).all()
    for fz in freezers:
        if st.button(f"🧊 {fz.name}", key=f"btn_freezer_{fz.name}"):
            st.session_state.selected_freezer = fz.name
            st.session_state.selected_rack = None
            st.session_state.selected_box = None
            st.session_state.selected_well = None
            st.rerun()

def add_new_freezer(session):
    """Display form to add a new freezer"""
    with st.form("add_freezer_form"):
        new_freezer = st.text_input("Add New Freezer")
        add_submit = st.form_submit_button("Add Freezer")
        if add_submit and new_freezer:
            existing = session.query(Freezer).filter_by(name=new_freezer.strip()).first()
            if not existing:
                session.add(Freezer(name=new_freezer.strip()))
                session.commit()
                st.success(f"Added freezer '{new_freezer.strip()}'")
                st.rerun()
            else:
                st.error(f"Freezer '{new_freezer.strip()}' already exists")

def handle_freezer_deletion(freezer_name):
    """Handle the deletion of a freezer with confirmation"""
    def delete_freezer(session, freezer_name, **kwargs):
        """Delete a freezer from the database"""
        freezer_to_delete = session.query(Freezer).filter_by(name=freezer_name).first()
        if freezer_to_delete:
            session.delete(freezer_to_delete)
            session.commit()
            # Reset session state
            st.session_state.selected_freezer = None
            st.session_state.selected_rack = None
            st.session_state.selected_box = None
            st.session_state.selected_well = None
            return True
        return False
    
    # Use the common delete confirmation handler
    if handle_delete_confirmation("freezer", freezer_name, delete_freezer):
        st.rerun()