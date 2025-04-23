import streamlit as st
from db_utils import get_db_session
from model import Rack, Box
from sqlalchemy import text
from common import handle_delete_confirmation

def display_box_selection():
    """Display the box selection interface if a rack is selected"""
    if not st.session_state.selected_rack:
        return
    
    with get_db_session() as session:
        box_expanded = st.session_state.selected_box is None
        selected_rack = session.query(Rack).filter_by(
            id=st.session_state.selected_rack, 
            freezer_name=st.session_state.selected_freezer
        ).first()
        
        if not selected_rack:
            st.error(f"Rack {st.session_state.selected_rack} not found in freezer {st.session_state.selected_freezer}")
            return
        
        boxes = session.query(Box).filter_by(rack_id=selected_rack.id).all()
        box_map = {b.id: b.box_name for b in boxes}
        
        selected_box_name = None
        if st.session_state.selected_box:
            selected_box = session.query(Box).filter_by(
                id=st.session_state.selected_box,
                rack_id=selected_rack.id
            ).first()
            if selected_box:
                selected_box_name = selected_box.box_name or selected_box.id

        with st.expander("3⃣ Select Box" if box_expanded else f"✅ Box: {selected_box_name or st.session_state.selected_box}", expanded=box_expanded):
            display_rack_layout(selected_rack, box_map)
            display_box_form(session, selected_rack, boxes)
            
            if st.session_state.selected_box:
                selected_box = session.query(Box).filter_by(
                    id=st.session_state.selected_box,
                    rack_id=selected_rack.id,
                ).first()
                
                if selected_box:
                    handle_box_deletion(selected_box)

def display_rack_layout(selected_rack, box_map):
    """Display the rack layout with boxes as a grid"""
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown(f"##### 🧱 {selected_rack.id} Layout")
    with col2:
        if st.button("➖ Reset", key="reset_box_selection"):
            st.session_state.selected_box = None
            st.session_state.selected_well = None
            st.rerun()
    
    for r in range(selected_rack.rows):
        cols = st.columns(selected_rack.columns)
        for c_ in range(selected_rack.columns):
            coord = f"{chr(65 + r)}{c_ + 1}"
            box_exists = coord in box_map
            label = box_map.get(coord, coord)
            with cols[c_]:
                if st.button(label[:10], key=f"btn_box_{coord}"):
                    if box_exists:
                        # If it's an existing box, select it
                        st.session_state.selected_box = coord
                        st.session_state.selected_well = None
                    else:
                        # If it's an empty slot, update the form position
                        st.session_state.box_form_position = coord
                    st.rerun()

def display_box_form(session, selected_rack, boxes):
    """Display form to add or edit a box"""
    if st.session_state.selected_box:
        selected_box = session.query(Box).filter_by(
            id=st.session_state.selected_box,
            rack_id=selected_rack.id,
        ).first()
    else:
        selected_box = None

    with st.form("box_form"):
        col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
        with col1:
            box_name = st.text_input("Box Name", value=selected_box.box_name if selected_box else "")
        with col2:
            box_user = st.text_input("User", value=selected_box.assigned_user if selected_box else "")
        with col3:
            box_rows = st.number_input("Rows", min_value=1, max_value=20, value=selected_box.rows if selected_box else 10)
        with col4:
            box_cols = st.number_input("Cols", min_value=1, max_value=20, value=selected_box.columns if selected_box else 10)
        with col5:
            all_coords = [f"{chr(65 + r)}{c + 1}" for r in range(selected_rack.rows) for c in range(selected_rack.columns)]
            occupied = {b.id for b in boxes if b.id != (selected_box.id if selected_box else None)}
            available_coords = [coord for coord in all_coords if coord not in occupied]
            box_position = st.selectbox(
                "Slot",
                options=available_coords,
                index=available_coords.index(st.session_state.box_form_position) if st.session_state.box_form_position in available_coords else (
                    available_coords.index(st.session_state.selected_box) if st.session_state.selected_box in available_coords else 0
                )
            )

        submitted = st.form_submit_button("Save Box")
        if submitted and box_name and box_user:
            save_box(session, selected_box, selected_rack, box_name, box_user, box_rows, box_cols, box_position)

def save_box(session, selected_box, selected_rack, box_name, box_user, box_rows, box_cols, box_position):
    """Save a new box or update an existing one"""
    if selected_box:
        selected_box.box_name = box_name.strip()
        selected_box.assigned_user = box_user.strip()
        selected_box.rows = box_rows
        selected_box.columns = box_cols

        if box_position != selected_box.id:
            # update id but preserve samples
            session.execute(
                text("UPDATE samples SET box = :new_id WHERE box = :old_id AND rack = :rack AND freezer = :freezer"), 
                {
                    "new_id": box_position,
                    "old_id": selected_box.id,
                    "rack": selected_rack.id,
                    "freezer": selected_rack.freezer_name
                }
            )
            selected_box.id = box_position
            st.session_state.selected_box = box_position

        session.commit()
        st.success(f"Updated box '{box_position}'")
        st.rerun()
    else:
        session.add(Box(
            id=box_position,
            rack_id=selected_rack.id,
            freezer_name=selected_rack.freezer_name,
            box_name=box_name.strip(),
            assigned_user=box_user.strip(),
            rows=box_rows,
            columns=box_cols
        ))
        session.commit()
        st.success(f"Added new box '{box_position}'")
        st.session_state.selected_box = box_position
        st.rerun()

def handle_box_deletion(selected_box):
    """Handle the deletion of a box with confirmation"""
    def delete_box(session, box_id, **kwargs):
        """Delete a box from the database"""
        box_to_delete = session.query(Box).filter_by(
            id=box_id,
            rack_id=selected_box.rack_id,
            freezer_name=selected_box.freezer_name
        ).first()
        if box_to_delete:
            session.delete(box_to_delete)
            session.commit()
            # Reset session state
            st.session_state.selected_box = None
            st.session_state.selected_well = None
            return True
        return False
    
    # Use the common delete confirmation handler
    additional_params = {
        "rack_id": selected_box.rack_id,
        "freezer_name": selected_box.freezer_name
    }
    if handle_delete_confirmation("box", selected_box.id, delete_box, additional_params):
        st.rerun()