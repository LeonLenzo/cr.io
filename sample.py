import streamlit as st
import pandas as pd
from datetime import datetime
from db_utils import get_db_session
from model import Box, Sample
from data_validation import validate_sample_form, validate_csv_upload, ValidationError, sanitize_input
from sample_history import log_sample_creation, log_sample_update, log_sample_deletion, log_bulk_sample_changes, display_sample_audit_trail
from auth import require_login

@require_login
def display_sample_management():
    """Display the sample management interface if a box is selected"""
    if not st.session_state.selected_box:
        return
    
    with get_db_session() as session:
        selected_box = session.query(Box).filter_by(
            id=st.session_state.selected_box,
            rack_id=st.session_state.selected_rack,
            freezer_name=st.session_state.selected_freezer
        ).first()

        if selected_box is None:
            st.warning(f"No box exists at position {st.session_state.selected_box}. Please add a box first.")
            st.session_state.selected_box = None
            st.rerun()
        else:
            box_display = selected_box.box_name or selected_box.id
            
            with st.expander(f"4⃣ Manage Samples in Box: {box_display}", expanded=True):
                # Create tabs
                tabs = st.tabs(["Box Layout", "Add/Edit Sample", "Bulk Upload", "Sample History"])
                
                # If a well was just selected, show a message to click on the Add/Edit Sample tab
                if "switch_to_sample_form" in st.session_state and st.session_state.switch_to_sample_form:
                    st.info("Click on the 'Add/Edit Sample' tab to edit.")
                    st.session_state.switch_to_sample_form = False
                
                # Show all tabs normally
                with tabs[0]:
                    display_box_layout(session, selected_box)
                with tabs[1]:
                    display_sample_form(session, selected_box)
                with tabs[2]:
                    display_bulk_upload(session, selected_box)
                with tabs[3]:
                    display_box_history(session, selected_box)

def display_box_layout(session, selected_box):
    """Display the box layout with samples as a grid"""
    box_rows, box_cols = selected_box.rows, selected_box.columns
    samples = session.query(Sample).filter_by(
        freezer=selected_box.freezer_name,
        rack=selected_box.rack_id,
        box=selected_box.id
    ).all()
    filled = {s.well: s.sample_name for s in samples}

    st.markdown("#### 📊 Box Layout")
    for r in range(box_rows):
        cols = st.columns(box_cols)
        for c_ in range(box_cols):
            well = f"{chr(65 + r)}{c_ + 1}"
            label = filled.get(well, "")
            with cols[c_]:
                if st.button(label[:10] if label else well, key=f"btn_sample_{well}"):
                    st.session_state.selected_well = well
                    # Set flag to switch to the Add/Edit Sample tab
                    st.session_state.switch_to_sample_form = True
                    st.rerun()

def display_sample_form(session, selected_box):
    """Display form to add or edit a sample"""
    st.markdown("---")
    st.markdown("➕ Add/Edit Sample")
    prefill = {}
    if st.session_state.selected_well:
        st.markdown(f"**Selected Well:** {st.session_state.selected_well}")
        sample = session.query(Sample).filter_by(
            freezer=selected_box.freezer_name,
            rack=selected_box.rack_id,
            box=selected_box.id,
            well=st.session_state.selected_well
        ).first()
        if sample:
            prefill = {
                "sample_name": sample.sample_name,
                "sample_type": sample.sample_type,
                "owner": sample.owner,
                "notes": sample.notes,
                "species": sample.species,
                "resistance": sample.resistance,
                "date_created": sample.date_created,
                "strain": sample.strain,
                "ogtr": sample.ogtr,
                "daff": sample.daff
            }

        with st.form("sample_form"):
            row1_col1, row1_col2, row1_col3 = st.columns([2, 1, 1])
            with row1_col1:
                sample_name = st.text_input("Sample Name/ID", value=prefill.get("sample_name", ""))
            with row1_col2:
                sample_type_default = prefill.get("sample_type") or "Cell Line"
                sample_type = st.selectbox(
                    "Sample Type",
                    ["Cell Line", "DNA", "RNA", "Protein", "Other"],
                    index=["Cell Line", "DNA", "RNA", "Protein", "Other"].index(sample_type_default)
                )
            with row1_col3:
                well = st.text_input("Well", value=st.session_state.selected_well or "", placeholder="e.g., A1")

            row2_col1, row2_col2 = st.columns([1, 2])
            with row2_col1:
                owner = st.text_input("Owner", value=prefill.get("owner", ""))
            with row2_col2:
                notes = st.text_area("Notes", value=prefill.get("notes", ""))

            # Add date created and strain fields
            row3_col1, row3_col2 = st.columns(2)
            with row3_col1:
                date_created = st.text_input("Date Created", value=prefill.get("date_created", ""))
            with row3_col2:
                strain = st.text_input("Strain", value=prefill.get("strain", ""))
            
            if sample_type == "Cell Line":
                # Species and resistance
                cell_col1, cell_col2 = st.columns(2)
                with cell_col1:
                    species = st.text_input("Species", value=prefill.get("species", ""))
                with cell_col2:
                    resistance = st.text_input("Resistance", value=prefill.get("resistance", ""))
                
                # OGTR options
                st.subheader("OGTR")
                ogtr_options = ["Wildtype", "NLRD", "DNIR"]
                ogtr_default = prefill.get("ogtr", "").split(",") if prefill.get("ogtr") else []
                ogtr_selected = []
                ogtr_cols = st.columns(len(ogtr_options))
                for i, option in enumerate(ogtr_options):
                    with ogtr_cols[i]:
                        if st.checkbox(option, value=option in ogtr_default, key=f"ogtr_{option}"):
                            ogtr_selected.append(option)
                ogtr = ",".join(ogtr_selected)
                
                # DAFF options
                st.subheader("DAFF")
                daff_options = ["State Quarantine", "Federal Quarantine"]
                daff_default = prefill.get("daff", "").split(",") if prefill.get("daff") else []
                daff_selected = []
                daff_cols = st.columns(len(daff_options))
                for i, option in enumerate(daff_options):
                    with daff_cols[i]:
                        if st.checkbox(option, value=option in daff_default, key=f"daff_{option}"):
                            daff_selected.append(option)
                daff = ",".join(daff_selected)
            else:
                species = resistance = ""
                ogtr = daff = ""

            submitted = st.form_submit_button("Save Sample")
            if submitted:
                save_sample(session, sample, selected_box, sample_name, sample_type, well, owner, notes, species, resistance, date_created, strain, ogtr, daff)

        if st.session_state.selected_well and prefill:
            handle_sample_deletion(session, selected_box)

def save_sample(session, sample, selected_box, sample_name, sample_type, well, owner, notes, species, resistance, date_created, strain, ogtr, daff):
    """Save a new sample or update an existing one with validation and history tracking"""
    try:
        # Sanitize inputs
        sample_name = sanitize_input(sample_name)
        well = sanitize_input(well)
        owner = sanitize_input(owner)
        notes = sanitize_input(notes)
        species = sanitize_input(species)
        resistance = sanitize_input(resistance)
        date_created = sanitize_input(date_created)
        strain = sanitize_input(strain)
        ogtr = sanitize_input(ogtr)
        daff = sanitize_input(daff)
        
        # Validate sample data
        validate_sample_form(
            selected_box.freezer_name,
            selected_box.rack_id,
            selected_box.id,
            well,
            sample_name,
            sample_type,
            sample.id if sample else None
        )
        
        if sample:
            # Track changes for history
            changes = []
            
            if sample.sample_name != sample_name:
                changes.append(("sample_name", sample.sample_name, sample_name))
            
            if sample.sample_type != sample_type:
                changes.append(("sample_type", sample.sample_type, sample_type))
            
            if sample.well != well:
                changes.append(("well", sample.well, well))
            
            if sample.owner != owner:
                changes.append(("owner", sample.owner, owner))
            
            if sample.notes != notes:
                changes.append(("notes", sample.notes, notes))
            
            if sample.species != species:
                changes.append(("species", sample.species, species))
            
            if sample.resistance != resistance:
                changes.append(("resistance", sample.resistance, resistance))
            
            if sample.date_created != date_created:
                changes.append(("date_created", sample.date_created, date_created))
            
            if sample.strain != strain:
                changes.append(("strain", sample.strain, strain))
            
            if sample.ogtr != ogtr:
                changes.append(("ogtr", sample.ogtr, ogtr))
            
            if sample.daff != daff:
                changes.append(("daff", sample.daff, daff))
            
            # Update sample
            sample.sample_name = sample_name
            sample.sample_type = sample_type
            sample.well = well
            sample.owner = owner
            sample.notes = notes
            sample.species = species
            sample.resistance = resistance
            sample.date_created = date_created
            sample.strain = strain
            sample.ogtr = ogtr
            sample.daff = daff
            
            session.commit()
            
            # Log changes to history
            for field, old_value, new_value in changes:
                log_sample_update(sample, field, old_value, new_value)
            
            st.success(f"Sample '{sample_name}' updated in {well}.")
        else:
            # Create new sample
            new_sample = Sample(
                sample_name=sample_name,
                sample_type=sample_type,
                freezer=selected_box.freezer_name,
                rack=selected_box.rack_id,
                box=selected_box.id,
                well=well,
                owner=owner,
                notes=notes,
                species=species,
                resistance=resistance,
                date_created=date_created,
                strain=strain,
                ogtr=ogtr,
                daff=daff,
                box_id=selected_box.id,
                rack_id=selected_box.rack_id,
                freezer_name=selected_box.freezer_name
            )
            session.add(new_sample)
            session.commit()
            
            # Log sample creation
            log_sample_creation(new_sample)
            
            st.success(f"Sample '{sample_name}' created in {well}.")
        
        st.rerun()
    except ValidationError as e:
        st.error(f"Validation error: {str(e)}")
    except Exception as e:
        st.error(f"Error saving sample: {str(e)}")

def handle_sample_deletion(session, selected_box):
    """Handle the deletion of a sample with confirmation and history tracking"""
    if st.button("Delete Sample"):
        sample_to_delete = session.query(Sample).filter_by(
            freezer=selected_box.freezer_name,
            rack=selected_box.rack_id,
            box=selected_box.id,
            well=st.session_state.selected_well
        ).first()
        
        if sample_to_delete:
            # Ask for confirmation
            st.warning(f"⚠️ Are you sure you want to delete sample '{sample_to_delete.sample_name}' from {st.session_state.selected_well}?")
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("Yes, Delete", key="confirm_delete"):
                    # Log deletion before deleting
                    log_sample_deletion(sample_to_delete)
                    
                    # Delete the sample
                    session.delete(sample_to_delete)
                    session.commit()
                    
                    st.success(f"Sample deleted from {st.session_state.selected_well}.")
                    st.session_state.selected_well = None
                    st.rerun()
            with col2:
                if st.button("Cancel", key="cancel_delete"):
                    st.rerun()

def display_bulk_upload(session, selected_box):
    """Display the bulk upload interface for samples"""
    freezer = st.session_state.selected_freezer
    rack = st.session_state.selected_rack
    box = st.session_state.selected_box
    
    # Fetch the selected box to get its name
    box_info = session.query(Box).filter_by(
        freezer_name=freezer,
        rack_id=rack,
        id=box
    ).first()
    
    if not box_info:
        st.warning("Box not found for bulk upload.")
        return
    
    box_rows = box_info.rows
    box_cols = box_info.columns
    
    # Get the box name for display
    box_display_name = box_info.box_name or box_info.id

    st.markdown("---")
    st.markdown(f"### 📂 Bulk Upload Samples for {box_display_name}")
    st.write("Download your box in tabular form to quickly update multiple samples. Then reupload to apply changes.")

    all_wells = [f"{chr(65 + r)}{c+1}" for r in range(box_rows) for c in range(box_cols)]

    samples = session.query(Sample).filter_by(
        freezer=freezer,
        rack=rack,
        box=box
    ).all()
    existing = {s.well: s for s in samples}

    columns = ["freezer", "rack", "box", "well", "sample_name", "sample_type", "owner", "notes", "species", "resistance", "date_created", "strain", "ogtr", "daff"]
    data = []
    for well in all_wells:
        s = existing.get(well)
        if s:
            data.append([
                s.freezer, s.rack, s.box, s.well,
                s.sample_name, s.sample_type, s.owner,
                s.notes, s.species, s.resistance, s.date_created, s.strain, s.ogtr, s.daff
            ])
        else:
            data.append([freezer, rack, box, well, "", "", "", "", "", "", "", "", "", ""])

    df = pd.DataFrame(data, columns=columns)
    
    # Use the box name in the file name for downloaded template
    st.download_button("Download CSV Template", 
                    df.to_csv(index=False).encode("utf-8"), 
                    file_name=f"{box_display_name}.csv", 
                    mime="text/csv")

    uploaded = st.file_uploader("Upload your filled CSV template", type="csv")
    if uploaded:
        process_uploaded_csv(session, uploaded)

def process_uploaded_csv(session, uploaded):
    """Process an uploaded CSV file with sample data, validation, and history tracking"""
    try:
        # Use Latin-1 encoding which we know works
        df_upload = pd.read_csv(uploaded, encoding='latin1')
        
        # Validate the CSV format and content
        freezer = st.session_state.selected_freezer
        rack = st.session_state.selected_rack
        box = st.session_state.selected_box
        
        is_valid, errors = validate_csv_upload(df_upload, freezer, rack, box)
        
        if not is_valid:
            st.error("CSV validation failed:")
            for error in errors:
                st.error(f"- {error}")
            return
        
        # Track changes for history
        added_samples = []
        updated_samples = []
        deleted_samples = []
        
        # Process the uploaded data
        for _, row in df_upload.iterrows():
            # Skip rows that don't match our box
            if row["freezer"] != freezer or row["rack"] != rack or row["box"] != box:
                continue
                
            existing_sample = session.query(Sample).filter_by(
                freezer=row["freezer"], rack=row["rack"], box=row["box"], well=row["well"]
            ).first()

            if pd.isna(row["sample_name"]) or str(row["sample_name"]).strip() == "":
                # Delete sample if name is empty
                if existing_sample:
                    deleted_samples.append(existing_sample)
                    session.delete(existing_sample)
            else:
                # Sanitize inputs
                for col in ["sample_name", "sample_type", "owner", "notes", "species", "resistance", "date_created", "strain", "ogtr", "daff"]:
                    if col in row:
                        row[col] = sanitize_input(row[col])
                
                if existing_sample:
                    # Track changes
                    changes = []
                    for col in ["sample_name", "sample_type", "owner", "notes", "species", "resistance", "date_created", "strain", "ogtr", "daff"]:
                        old_value = getattr(existing_sample, col)
                        new_value = row[col]
                        if old_value != new_value:
                            changes.append((existing_sample, col, old_value, new_value))
                    
                    # Update sample
                    for col in ["sample_name", "sample_type", "owner", "notes", "species", "resistance", "date_created", "strain", "ogtr", "daff"]:
                        setattr(existing_sample, col, row[col])
                    
                    if changes:
                        updated_samples.extend(changes)
                else:
                    # Create new sample
                    new_s = Sample(
                        freezer=row["freezer"],
                        rack=row["rack"],
                        box=row["box"],
                        well=row["well"],
                        sample_name=row["sample_name"],
                        sample_type=row["sample_type"],
                        owner=row["owner"],
                        notes=row["notes"],
                        species=row["species"],
                        resistance=row["resistance"],
                        date_created=row["date_created"],
                        strain=row["strain"],
                        ogtr=row["ogtr"],
                        daff=row["daff"],
                        box_id=row["box"],
                        rack_id=row["rack"],
                        freezer_name=row["freezer"]
                    )
                    session.add(new_s)
                    added_samples.append(new_s)
        
        # Commit changes
        session.commit()
        
        # Log changes to history
        log_bulk_sample_changes(added_samples, updated_samples, deleted_samples)
        
        # Show summary
        st.success(f"Sample data updated successfully: {len(added_samples)} added, {len(updated_samples)} updated, {len(deleted_samples)} deleted.")
        st.rerun()
    except Exception as e:
        st.error(f"Upload failed: {e}")
        import traceback
        st.error(traceback.format_exc())

def display_box_history(session, selected_box):
    """Display history for samples in the selected box"""
    st.subheader(f"Sample History for Box: {selected_box.box_name or selected_box.id}")
    
    # Get samples in this box
    samples = session.query(Sample).filter_by(
        freezer=selected_box.freezer_name,
        rack=selected_box.rack_id,
        box=selected_box.id
    ).all()
    
    if not samples:
        st.info("No samples found in this box.")
        return
    
    # Create a selection for which sample to view history for
    sample_options = [f"{s.well}: {s.sample_name}" for s in samples]
    selected_sample_display = st.selectbox(
        "Select Sample to View History",
        options=[""] + sample_options
    )
    
    if selected_sample_display:
        # Extract well from display name
        well = selected_sample_display.split(":")[0].strip()
        
        # Find the sample
        sample = next((s for s in samples if s.well == well), None)
        
        if sample:
            # Display audit trail for this sample
            display_sample_audit_trail(sample)