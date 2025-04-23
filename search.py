import streamlit as st
import pandas as pd
import json
from datetime import datetime
from db_utils import get_db_session
from model import Sample, Freezer, Rack, Box
from auth import require_login

@require_login
def display_search_interface():
    """Display the search interface and handle search functionality"""
    st.markdown("## 🔍 Search Samples")
    
    # Create tabs for basic and advanced search
    search_tabs = st.tabs(["Basic Search", "Advanced Search", "Saved Searches"])
    
    with search_tabs[0]:
        display_basic_search()
    
    with search_tabs[1]:
        display_advanced_search()
    
    with search_tabs[2]:
        display_saved_searches()

def display_basic_search():
    """Display the basic search interface"""
    search_query = st.text_input("Enter Keyword: (name, type, owner, etc.)", key="basic_search")
    
    if search_query:
        with get_db_session() as session:
            search_results = perform_basic_search(session, search_query)
            display_search_results(search_results, f"Basic search for '{search_query}'")

def display_advanced_search():
    """Display the advanced search interface with multiple filters"""
    with st.form("advanced_search_form"):
        st.subheader("Advanced Search")
        
        col1, col2 = st.columns(2)
        
        with col1:
            sample_name = st.text_input("Sample Name")
            sample_type = st.selectbox(
                "Sample Type",
                options=["", "Cell Line", "DNA", "RNA", "Protein", "Other"]
            )
            owner = st.text_input("Owner")
        
        with col2:
            with get_db_session() as session:
                freezers = [""] + [f[0] for f in session.query(Freezer.name).all()]
                freezer = st.selectbox("Freezer", options=freezers)
                
                if freezer:
                    racks = [""] + [r[0] for r in session.query(Rack.id).filter_by(freezer_name=freezer).all()]
                else:
                    racks = [""]
                rack = st.selectbox("Rack", options=racks)
                
                if freezer and rack:
                    boxes = [""] + [b[0] for b in session.query(Box.id).filter_by(freezer_name=freezer, rack_id=rack).all()]
                else:
                    boxes = [""]
                box = st.selectbox("Box", options=boxes)
        
        col1, col2 = st.columns(2)
        with col1:
            species = st.text_input("Species")
            resistance = st.text_input("Resistance")
        
        with col2:
            regulation = st.text_input("Regulation")
            notes_keywords = st.text_input("Notes Keywords")
        
        # Date range filter
        st.subheader("Date Range")
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", value=None)
        with date_col2:
            end_date = st.date_input("End Date", value=None)
        
        # Save search option
        save_search = st.checkbox("Save this search for later")
        if save_search:
            search_name = st.text_input("Search Name")
        
        submitted = st.form_submit_button("Search")
        
        if submitted:
            # Build search criteria
            search_criteria = {}
            
            if sample_name:
                search_criteria["sample_name"] = sample_name
            if sample_type:
                search_criteria["sample_type"] = sample_type
            if owner:
                search_criteria["owner"] = owner
            if freezer:
                search_criteria["freezer"] = freezer
            if rack:
                search_criteria["rack"] = rack
            if box:
                search_criteria["box"] = box
            if species:
                search_criteria["species"] = species
            if resistance:
                search_criteria["resistance"] = resistance
            if regulation:
                search_criteria["regulation"] = regulation
            if notes_keywords:
                search_criteria["notes"] = notes_keywords
            if start_date:
                search_criteria["start_date"] = start_date.isoformat()
            if end_date:
                search_criteria["end_date"] = end_date.isoformat()
            
            # Save search if requested
            if save_search and search_name:
                save_search_criteria(search_name, search_criteria)
            
            # Perform search
            with get_db_session() as session:
                search_results = perform_advanced_search(session, search_criteria)
                display_search_results(search_results, "Advanced search results")

def display_saved_searches():
    """Display and manage saved searches"""
    # Load saved searches
    saved_searches = load_saved_searches()
    
    if not saved_searches:
        st.info("No saved searches found. Use the Advanced Search tab to create and save searches.")
        return
    
    # Display saved searches
    st.subheader("Your Saved Searches")
    
    selected_search = st.selectbox(
        "Select a saved search",
        options=list(saved_searches.keys())
    )
    
    if selected_search:
        search_criteria = saved_searches[selected_search]
        
        # Display search criteria
        st.write("**Search Criteria:**")
        criteria_display = {k: v for k, v in search_criteria.items() if v}
        st.json(criteria_display)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Run Search"):
                with get_db_session() as session:
                    search_results = perform_advanced_search(session, search_criteria)
                    display_search_results(search_results, f"Results for '{selected_search}'")
        
        with col2:
            if st.button("Delete Search"):
                delete_saved_search(selected_search)
                st.success(f"Deleted saved search: {selected_search}")
                st.rerun()
        
        with col3:
            if st.button("Edit Search"):
                st.session_state.edit_search_name = selected_search
                st.session_state.edit_search_criteria = search_criteria
                st.rerun()
    
    # Edit search form
    if "edit_search_name" in st.session_state and st.session_state.edit_search_name:
        with st.form("edit_search_form"):
            st.subheader(f"Edit Search: {st.session_state.edit_search_name}")
            
            criteria = st.session_state.edit_search_criteria
            
            col1, col2 = st.columns(2)
            
            with col1:
                sample_name = st.text_input("Sample Name", value=criteria.get("sample_name", ""))
                sample_type = st.selectbox(
                    "Sample Type",
                    options=["", "Cell Line", "DNA", "RNA", "Protein", "Other"],
                    index=["", "Cell Line", "DNA", "RNA", "Protein", "Other"].index(criteria.get("sample_type", ""))
                )
                owner = st.text_input("Owner", value=criteria.get("owner", ""))
            
            with col2:
                freezer = st.text_input("Freezer", value=criteria.get("freezer", ""))
                rack = st.text_input("Rack", value=criteria.get("rack", ""))
                box = st.text_input("Box", value=criteria.get("box", ""))
            
            col1, col2 = st.columns(2)
            with col1:
                species = st.text_input("Species", value=criteria.get("species", ""))
                resistance = st.text_input("Resistance", value=criteria.get("resistance", ""))
            
            with col2:
                regulation = st.text_input("Regulation", value=criteria.get("regulation", ""))
                notes_keywords = st.text_input("Notes Keywords", value=criteria.get("notes", ""))
            
            # Date range filter
            st.subheader("Date Range")
            date_col1, date_col2 = st.columns(2)
            with date_col1:
                start_date = st.date_input(
                    "Start Date",
                    value=datetime.fromisoformat(criteria.get("start_date", "2020-01-01")) if "start_date" in criteria else None
                )
            with date_col2:
                end_date = st.date_input(
                    "End Date",
                    value=datetime.fromisoformat(criteria.get("end_date", "2020-01-01")) if "end_date" in criteria else None
                )
            
            new_name = st.text_input("Search Name", value=st.session_state.edit_search_name)
            
            submitted = st.form_submit_button("Update Search")
            
            if submitted:
                # Build updated search criteria
                updated_criteria = {}
                
                if sample_name:
                    updated_criteria["sample_name"] = sample_name
                if sample_type:
                    updated_criteria["sample_type"] = sample_type
                if owner:
                    updated_criteria["owner"] = owner
                if freezer:
                    updated_criteria["freezer"] = freezer
                if rack:
                    updated_criteria["rack"] = rack
                if box:
                    updated_criteria["box"] = box
                if species:
                    updated_criteria["species"] = species
                if resistance:
                    updated_criteria["resistance"] = resistance
                if regulation:
                    updated_criteria["regulation"] = regulation
                if notes_keywords:
                    updated_criteria["notes"] = notes_keywords
                if start_date:
                    updated_criteria["start_date"] = start_date.isoformat()
                if end_date:
                    updated_criteria["end_date"] = end_date.isoformat()
                
                # Update saved search
                update_saved_search(st.session_state.edit_search_name, new_name, updated_criteria)
                
                # Clear edit state
                st.session_state.edit_search_name = None
                st.session_state.edit_search_criteria = None
                
                st.success(f"Updated saved search: {new_name}")
                st.rerun()

def perform_basic_search(session, search_query):
    """
    Perform a basic search across multiple sample fields
    
    Parameters:
    - session: SQLAlchemy session
    - search_query: The search term to look for
    
    Returns:
    - List of dictionaries containing sample data
    """
    # Perform the search across multiple fields
    search_term = f"%{search_query}%"
    samples = session.query(Sample).filter(
        (Sample.sample_name.like(search_term)) |
        (Sample.sample_type.like(search_term)) |
        (Sample.owner.like(search_term)) |
        (Sample.notes.like(search_term)) |
        (Sample.species.like(search_term)) |
        (Sample.resistance.like(search_term)) |
        (Sample.regulation.like(search_term))
    ).all()
    
    # Convert Sample objects to dictionaries to avoid detached instance errors
    results = []
    for sample in samples:
        results.append({
            "sample_name": sample.sample_name,
            "sample_type": sample.sample_type,
            "freezer": sample.freezer,
            "rack": sample.rack,
            "box": sample.box,
            "well": sample.well,
            "owner": sample.owner,
            "date_added": sample.date_added.strftime("%Y-%m-%d") if sample.date_added else "",
            "notes": sample.notes,
            "species": sample.species,
            "resistance": sample.resistance,
            "regulation": sample.regulation,
            "id": sample.id
        })
    
    return results

def perform_advanced_search(session, criteria):
    """
    Perform an advanced search with multiple criteria
    
    Parameters:
    - session: SQLAlchemy session
    - criteria: Dictionary of search criteria
    
    Returns:
    - List of dictionaries containing sample data
    """
    # Start with base query
    query = session.query(Sample)
    
    # Apply filters based on criteria
    if "sample_name" in criteria and criteria["sample_name"]:
        query = query.filter(Sample.sample_name.like(f"%{criteria['sample_name']}%"))
    
    if "sample_type" in criteria and criteria["sample_type"]:
        query = query.filter(Sample.sample_type == criteria["sample_type"])
    
    if "owner" in criteria and criteria["owner"]:
        query = query.filter(Sample.owner.like(f"%{criteria['owner']}%"))
    
    if "freezer" in criteria and criteria["freezer"]:
        query = query.filter(Sample.freezer == criteria["freezer"])
    
    if "rack" in criteria and criteria["rack"]:
        query = query.filter(Sample.rack == criteria["rack"])
    
    if "box" in criteria and criteria["box"]:
        query = query.filter(Sample.box == criteria["box"])
    
    if "species" in criteria and criteria["species"]:
        query = query.filter(Sample.species.like(f"%{criteria['species']}%"))
    
    if "resistance" in criteria and criteria["resistance"]:
        query = query.filter(Sample.resistance.like(f"%{criteria['resistance']}%"))
    
    if "regulation" in criteria and criteria["regulation"]:
        query = query.filter(Sample.regulation.like(f"%{criteria['regulation']}%"))
    
    if "notes" in criteria and criteria["notes"]:
        query = query.filter(Sample.notes.like(f"%{criteria['notes']}%"))
    
    # Date range filters
    if "start_date" in criteria and criteria["start_date"]:
        start_date = datetime.fromisoformat(criteria["start_date"])
        query = query.filter(Sample.date_added >= start_date)
    
    if "end_date" in criteria and criteria["end_date"]:
        end_date = datetime.fromisoformat(criteria["end_date"])
        end_date = datetime.combine(end_date, datetime.max.time())  # Set to end of day
        query = query.filter(Sample.date_added <= end_date)
    
    # Execute query
    samples = query.all()
    
    # Convert Sample objects to dictionaries to avoid detached instance errors
    results = []
    for sample in samples:
        results.append({
            "sample_name": sample.sample_name,
            "sample_type": sample.sample_type,
            "freezer": sample.freezer,
            "rack": sample.rack,
            "box": sample.box,
            "well": sample.well,
            "owner": sample.owner,
            "date_added": sample.date_added.strftime("%Y-%m-%d") if sample.date_added else "",
            "notes": sample.notes,
            "species": sample.species,
            "resistance": sample.resistance,
            "regulation": sample.regulation,
            "id": sample.id
        })
    
    return results

def display_search_results(results, search_title):
    """
    Display search results in a dataframe with download and location jump options
    
    Parameters:
    - results: List of dictionaries containing sample data
    - search_title: Title for the search results
    """
    if results:
        # Convert to DataFrame with display-friendly column names
        data = []
        for sample in results:
            data.append({
                "Sample Name": sample["sample_name"],
                "Type": sample["sample_type"],
                "Freezer": sample["freezer"],
                "Rack": sample["rack"],
                "Box": sample["box"],
                "Well": sample["well"],
                "Owner": sample["owner"],
                "Date Added": sample["date_added"],
                "Notes": sample["notes"],
                "Species": sample["species"],
                "Resistance": sample["resistance"],
                "Regulation": sample["regulation"]
            })
        
        df = pd.DataFrame(data)
        
        # Display results
        st.subheader(f"{search_title} - Found {len(results)} matching samples")
        
        # Add filter options
        st.subheader("Filter Results")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            filter_type = st.multiselect(
                "Filter by Type",
                options=sorted(df["Type"].unique().tolist()),
                default=[]
            )
        
        with col2:
            filter_owner = st.multiselect(
                "Filter by Owner",
                options=sorted(df["Owner"].unique().tolist()),
                default=[]
            )
        
        with col3:
            filter_freezer = st.multiselect(
                "Filter by Freezer",
                options=sorted(df["Freezer"].unique().tolist()),
                default=[]
            )
        
        # Apply filters
        filtered_df = df.copy()
        
        if filter_type:
            filtered_df = filtered_df[filtered_df["Type"].isin(filter_type)]
        
        if filter_owner:
            filtered_df = filtered_df[filtered_df["Owner"].isin(filter_owner)]
        
        if filter_freezer:
            filtered_df = filtered_df[filtered_df["Freezer"].isin(filter_freezer)]
        
        # Show filter summary
        if filter_type or filter_owner or filter_freezer:
            st.write(f"Showing {len(filtered_df)} of {len(df)} samples after filtering")
        else:
            st.write("No filters applied")
        
        # Display filtered results
        st.dataframe(filtered_df, use_container_width=True)
        
        # Add download button
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Download Results",
            csv,
            f"search_results.csv",
            "text/csv",
            key='download-csv'
        )
        
        # Add location jump buttons
        st.write("Jump to location:")
        
        # Group samples by freezer/rack/box for more organized display
        locations = {}
        for i, sample in enumerate(results):
            location_key = f"{sample['freezer']}/{sample['rack']}/{sample['box']}"
            if location_key not in locations:
                locations[location_key] = []
            locations[location_key].append((i, sample))
        
        # Display grouped by location
        for location, samples in locations.items():
            with st.expander(f"Location: {location}"):
                for i, sample in samples:
                    if st.button(f"Go to {sample['sample_name']} (Well: {sample['well']})", key=f"goto_{i}"):
                        st.session_state.selected_freezer = sample["freezer"]
                        st.session_state.selected_rack = sample["rack"]
                        st.session_state.selected_box = sample["box"]
                        st.session_state.selected_well = sample["well"]
                        st.rerun()
    else:
        st.warning("No samples found matching your search criteria")

def save_search_criteria(name, criteria):
    """
    Save search criteria to session state and to a file
    
    Parameters:
    - name: Name of the saved search
    - criteria: Dictionary of search criteria
    """
    # Load existing saved searches
    saved_searches = load_saved_searches()
    
    # Add or update this search
    saved_searches[name] = criteria
    
    # Save to session state
    st.session_state.saved_searches = saved_searches
    
    # Save to file
    try:
        with open("saved_searches.json", "w") as f:
            json.dump(saved_searches, f)
    except Exception as e:
        st.error(f"Error saving search: {e}")

def load_saved_searches():
    """
    Load saved searches from file or session state
    
    Returns:
    - Dictionary of saved searches
    """
    if "saved_searches" in st.session_state:
        return st.session_state.saved_searches
    
    try:
        with open("saved_searches.json", "r") as f:
            saved_searches = json.load(f)
            st.session_state.saved_searches = saved_searches
            return saved_searches
    except FileNotFoundError:
        st.session_state.saved_searches = {}
        return {}
    except Exception as e:
        st.error(f"Error loading saved searches: {e}")
        return {}

def delete_saved_search(name):
    """
    Delete a saved search
    
    Parameters:
    - name: Name of the saved search to delete
    """
    # Load existing saved searches
    saved_searches = load_saved_searches()
    
    # Remove this search
    if name in saved_searches:
        del saved_searches[name]
    
    # Update session state
    st.session_state.saved_searches = saved_searches
    
    # Save to file
    try:
        with open("saved_searches.json", "w") as f:
            json.dump(saved_searches, f)
    except Exception as e:
        st.error(f"Error saving changes: {e}")

def update_saved_search(old_name, new_name, criteria):
    """
    Update a saved search
    
    Parameters:
    - old_name: Current name of the saved search
    - new_name: New name for the saved search
    - criteria: Updated search criteria
    """
    # Load existing saved searches
    saved_searches = load_saved_searches()
    
    # Remove old search
    if old_name in saved_searches:
        del saved_searches[old_name]
    
    # Add updated search
    saved_searches[new_name] = criteria
    
    # Update session state
    st.session_state.saved_searches = saved_searches
    
    # Save to file
    try:
        with open("saved_searches.json", "w") as f:
            json.dump(saved_searches, f)
    except Exception as e:
        st.error(f"Error saving changes: {e}")