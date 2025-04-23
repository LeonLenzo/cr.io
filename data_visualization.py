import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from sqlalchemy import func
from db_utils import get_db_session
from model import Sample, Freezer, Rack, Box
from auth import require_login

@require_login
def display_data_visualization():
    """Display data visualization dashboard"""
    tabs = st.tabs(["Sample Overview", "Storage Utilization", "Sample Timeline", "Custom Analysis"])
    
    with tabs[0]:
        display_sample_overview()
    
    with tabs[1]:
        display_storage_utilization()
    
    with tabs[2]:
        display_sample_timeline()
    
    with tabs[3]:
        display_custom_analysis()

def display_sample_overview():
    """Display overview of samples by type, owner, etc."""
    st.subheader("Sample Overview")
    
    with get_db_session() as session:
        # Get total sample count
        total_samples = session.query(Sample).count()
        
        if total_samples == 0:
            st.warning("No samples found in the database.")
            return
        
        st.metric("Total Samples", total_samples)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Sample distribution by type
            sample_types = session.query(
                Sample.sample_type,
                func.count(Sample.id).label('count')
            ).group_by(Sample.sample_type).all()
            
            if sample_types:
                df_types = pd.DataFrame(sample_types, columns=['Sample Type', 'Count'])
                
                fig = px.pie(
                    df_types, 
                    values='Count', 
                    names='Sample Type',
                    title='Sample Distribution by Type',
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Sample distribution by owner
            sample_owners = session.query(
                Sample.owner,
                func.count(Sample.id).label('count')
            ).group_by(Sample.owner).all()
            
            if sample_owners:
                df_owners = pd.DataFrame(sample_owners, columns=['Owner', 'Count'])
                df_owners = df_owners.sort_values('Count', ascending=False)
                
                fig = px.bar(
                    df_owners, 
                    x='Owner', 
                    y='Count',
                    title='Sample Distribution by Owner',
                    color='Count',
                    color_continuous_scale='Viridis'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Species distribution (for Cell Line samples)
        cell_line_species = session.query(
            Sample.species,
            func.count(Sample.id).label('count')
        ).filter(
            Sample.sample_type == 'Cell Line',
            Sample.species != ''
        ).group_by(Sample.species).all()
        
        if cell_line_species:
            df_species = pd.DataFrame(cell_line_species, columns=['Species', 'Count'])
            df_species = df_species.sort_values('Count', ascending=False)
            
            # Limit to top 10 species for readability
            if len(df_species) > 10:
                other_count = df_species.iloc[10:]['Count'].sum()
                df_species = df_species.iloc[:10]
                df_species = pd.concat([
                    df_species, 
                    pd.DataFrame([{'Species': 'Other', 'Count': other_count}])
                ])
            
            fig = px.bar(
                df_species, 
                x='Species', 
                y='Count',
                title='Cell Line Samples by Species',
                color='Species',
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            st.plotly_chart(fig, use_container_width=True)

def display_storage_utilization():
    """Display storage utilization metrics"""
    st.subheader("Storage Utilization")
    
    with get_db_session() as session:
        # Get freezer stats
        freezers = session.query(Freezer).all()
        
        if not freezers:
            st.warning("No freezers found in the database.")
            return
        
        freezer_stats = []
        for freezer in freezers:
            # Count racks in this freezer
            rack_count = session.query(Rack).filter_by(freezer_name=freezer.name).count()
            
            # Count boxes in this freezer
            box_count = session.query(Box).filter_by(freezer_name=freezer.name).count()
            
            # Count samples in this freezer
            sample_count = session.query(Sample).filter_by(freezer=freezer.name).count()
            
            freezer_stats.append({
                'Freezer': freezer.name,
                'Racks': rack_count,
                'Boxes': box_count,
                'Samples': sample_count
            })
        
        df_freezers = pd.DataFrame(freezer_stats)
        
        # Display freezer stats
        col1, col2 = st.columns(2)
        
        with col1:
            # Freezer comparison
            fig = px.bar(
                df_freezers, 
                x='Freezer', 
                y=['Racks', 'Boxes', 'Samples'],
                title='Storage by Freezer',
                barmode='group'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Box utilization
            box_utilization = []
            for freezer in freezers:
                boxes = session.query(Box).filter_by(freezer_name=freezer.name).all()
                
                for box in boxes:
                    # Calculate total capacity
                    capacity = box.rows * box.columns
                    
                    # Count samples in this box
                    sample_count = session.query(Sample).filter_by(
                        freezer=freezer.name,
                        rack=box.rack_id,
                        box=box.id
                    ).count()
                    
                    # Calculate utilization percentage
                    utilization = (sample_count / capacity) * 100 if capacity > 0 else 0
                    
                    box_utilization.append({
                        'Freezer': freezer.name,
                        'Rack': box.rack_id,
                        'Box': box.id,
                        'Box Name': box.box_name or box.id,
                        'Capacity': capacity,
                        'Samples': sample_count,
                        'Utilization (%)': utilization
                    })
            
            if box_utilization:
                df_utilization = pd.DataFrame(box_utilization)
                
                # Display top 10 most utilized boxes
                top_boxes = df_utilization.sort_values('Utilization (%)', ascending=False).head(10)
                
                fig = px.bar(
                    top_boxes, 
                    x='Box Name', 
                    y='Utilization (%)',
                    title='Top 10 Most Utilized Boxes',
                    color='Utilization (%)',
                    color_continuous_scale='RdYlGn_r',
                    hover_data=['Freezer', 'Rack', 'Samples', 'Capacity']
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Display freezer capacity heatmap
        st.subheader("Freezer Capacity Heatmap")
        
        selected_freezer = st.selectbox(
            "Select Freezer",
            options=[f.name for f in freezers]
        )
        
        if selected_freezer:
            # Get racks in this freezer
            racks = session.query(Rack).filter_by(freezer_name=selected_freezer).all()
            
            if not racks:
                st.warning(f"No racks found in freezer {selected_freezer}.")
            else:
                # Create a heatmap of box utilization
                for rack in racks:
                    st.write(f"**Rack: {rack.id}**")
                    
                    # Create a matrix for the heatmap
                    heatmap_data = []
                    for r in range(rack.rows):
                        row_data = []
                        for c in range(rack.columns):
                            coord = f"{chr(65 + r)}{c + 1}"
                            
                            # Check if a box exists at this position
                            box = session.query(Box).filter_by(
                                freezer_name=selected_freezer,
                                rack_id=rack.id,
                                id=coord
                            ).first()
                            
                            if box:
                                # Calculate box utilization
                                capacity = box.rows * box.columns
                                sample_count = session.query(Sample).filter_by(
                                    freezer=selected_freezer,
                                    rack=rack.id,
                                    box=coord
                                ).count()
                                
                                utilization = (sample_count / capacity) * 100 if capacity > 0 else 0
                                row_data.append(utilization)
                            else:
                                row_data.append(0)  # No box = 0% utilization
                        
                        heatmap_data.append(row_data)
                    
                    # Create heatmap
                    fig = go.Figure(data=go.Heatmap(
                        z=heatmap_data,
                        x=[f"{c+1}" for c in range(rack.columns)],
                        y=[chr(65 + r) for r in range(rack.rows)],
                        colorscale='RdYlGn_r',
                        showscale=True,
                        colorbar=dict(title='Utilization %')
                    ))
                    
                    fig.update_layout(
                        title=f"Box Utilization in Rack {rack.id}",
                        xaxis_title="Column",
                        yaxis_title="Row"
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)

def display_sample_timeline():
    """Display sample addition timeline"""
    st.subheader("Sample Timeline")
    
    with get_db_session() as session:
        # Get sample addition dates
        samples = session.query(Sample.date_added, Sample.sample_type).all()
        
        if not samples:
            st.warning("No samples found in the database.")
            return
        
        # Convert to DataFrame
        df_samples = pd.DataFrame(samples, columns=['Date Added', 'Sample Type'])
        
        # Ensure date is datetime
        df_samples['Date Added'] = pd.to_datetime(df_samples['Date Added'])
        
        # Filter out invalid dates
        df_samples = df_samples[df_samples['Date Added'].notna()]
        
        if df_samples.empty:
            st.warning("No valid dates found in sample data.")
            return
        
        # Group by date and type
        df_samples['Date'] = df_samples['Date Added'].dt.date
        timeline_data = df_samples.groupby(['Date', 'Sample Type']).size().reset_index(name='Count')
        
        # Create timeline chart
        fig = px.line(
            timeline_data, 
            x='Date', 
            y='Count',
            color='Sample Type',
            title='Sample Additions Over Time',
            markers=True
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Sample additions by month
        df_samples['Month'] = df_samples['Date Added'].dt.to_period('M')
        monthly_data = df_samples.groupby(['Month', 'Sample Type']).size().reset_index(name='Count')
        monthly_data['Month'] = monthly_data['Month'].astype(str)
        
        fig = px.bar(
            monthly_data, 
            x='Month', 
            y='Count',
            color='Sample Type',
            title='Monthly Sample Additions',
            barmode='stack'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Recent activity
        st.subheader("Recent Activity")
        
        # Get samples added in the last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_samples = session.query(Sample).filter(Sample.date_added >= thirty_days_ago).all()
        
        if not recent_samples:
            st.info("No samples added in the last 30 days.")
        else:
            # Convert to DataFrame
            recent_data = []
            for sample in recent_samples:
                recent_data.append({
                    'Date': sample.date_added.strftime('%Y-%m-%d'),
                    'Sample': sample.sample_name,
                    'Type': sample.sample_type,
                    'Location': f"{sample.freezer}/{sample.rack}/{sample.box}/{sample.well}",
                    'Owner': sample.owner
                })
            
            df_recent = pd.DataFrame(recent_data)
            st.dataframe(df_recent, use_container_width=True)

def display_custom_analysis():
    """Display custom analysis options"""
    st.subheader("Custom Analysis")
    
    analysis_type = st.selectbox(
        "Select Analysis Type",
        options=[
            "Sample Type Distribution by Freezer",
            "Owner Activity Analysis",
            "Sample Density by Location",
            "Species Distribution"
        ]
    )
    
    if analysis_type == "Sample Type Distribution by Freezer":
        display_sample_type_by_freezer()
    elif analysis_type == "Owner Activity Analysis":
        display_owner_activity()
    elif analysis_type == "Sample Density by Location":
        display_sample_density()
    elif analysis_type == "Species Distribution":
        display_species_distribution()

def display_sample_type_by_freezer():
    """Display sample type distribution by freezer"""
    with get_db_session() as session:
        # Get sample types by freezer
        query_result = session.query(
            Sample.freezer,
            Sample.sample_type,
            func.count(Sample.id).label('count')
        ).group_by(Sample.freezer, Sample.sample_type).all()
        
        if not query_result:
            st.warning("No data available for this analysis.")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(query_result, columns=['Freezer', 'Sample Type', 'Count'])
        
        # Create visualization
        fig = px.bar(
            df, 
            x='Freezer', 
            y='Count',
            color='Sample Type',
            title='Sample Type Distribution by Freezer',
            barmode='stack'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Show data table
        st.dataframe(df, use_container_width=True)

def display_owner_activity():
    """Display owner activity analysis"""
    with get_db_session() as session:
        # Get sample counts by owner and date
        samples = session.query(
            Sample.owner,
            Sample.date_added
        ).all()
        
        if not samples:
            st.warning("No data available for this analysis.")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(samples, columns=['Owner', 'Date Added'])
        
        # Ensure date is datetime
        df['Date Added'] = pd.to_datetime(df['Date Added'])
        
        # Filter out invalid dates
        df = df[df['Date Added'].notna()]
        
        if df.empty:
            st.warning("No valid dates found in sample data.")
            return
        
        # Group by owner and month
        df['Month'] = df['Date Added'].dt.to_period('M')
        activity_data = df.groupby(['Owner', 'Month']).size().reset_index(name='Samples Added')
        activity_data['Month'] = activity_data['Month'].astype(str)
        
        # Create visualization
        fig = px.line(
            activity_data, 
            x='Month', 
            y='Samples Added',
            color='Owner',
            title='Sample Addition Activity by Owner',
            markers=True
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Owner summary
        owner_summary = df.groupby('Owner').size().reset_index(name='Total Samples')
        owner_summary = owner_summary.sort_values('Total Samples', ascending=False)
        
        fig = px.pie(
            owner_summary, 
            values='Total Samples', 
            names='Owner',
            title='Total Samples by Owner',
            hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)

def display_sample_density():
    """Display sample density by location"""
    with get_db_session() as session:
        # Get freezers
        freezers = session.query(Freezer).all()
        
        if not freezers:
            st.warning("No freezers found in the database.")
            return
        
        selected_freezer = st.selectbox(
            "Select Freezer",
            options=[f.name for f in freezers]
        )
        
        if not selected_freezer:
            return
        
        # Get racks in this freezer
        racks = session.query(Rack).filter_by(freezer_name=selected_freezer).all()
        
        if not racks:
            st.warning(f"No racks found in freezer {selected_freezer}.")
            return
        
        selected_rack = st.selectbox(
            "Select Rack",
            options=[r.id for r in racks]
        )
        
        if not selected_rack:
            return
        
        # Get the selected rack
        rack = session.query(Rack).filter_by(
            freezer_name=selected_freezer,
            id=selected_rack
        ).first()
        
        if not rack:
            st.warning(f"Rack {selected_rack} not found in freezer {selected_freezer}.")
            return
        
        # Get boxes in this rack
        boxes = session.query(Box).filter_by(
            freezer_name=selected_freezer,
            rack_id=selected_rack
        ).all()
        
        if not boxes:
            st.warning(f"No boxes found in rack {selected_rack}.")
            return
        
        # Create a box selection
        box_options = [f"{b.id} - {b.box_name}" if b.box_name else b.id for b in boxes]
        selected_box_display = st.selectbox(
            "Select Box",
            options=box_options
        )
        
        if not selected_box_display:
            return
        
        # Extract box ID from display name
        selected_box = selected_box_display.split(" - ")[0]
        
        # Get the selected box
        box = session.query(Box).filter_by(
            freezer_name=selected_freezer,
            rack_id=selected_rack,
            id=selected_box
        ).first()
        
        if not box:
            st.warning(f"Box {selected_box} not found in rack {selected_rack}.")
            return
        
        # Get samples in this box
        samples = session.query(Sample).filter_by(
            freezer=selected_freezer,
            rack=selected_rack,
            box=selected_box
        ).all()
        
        # Create a matrix for the heatmap
        heatmap_data = []
        annotations = []
        
        for r in range(box.rows):
            row_data = []
            for c in range(box.columns):
                well = f"{chr(65 + r)}{c + 1}"
                
                # Check if a sample exists at this position
                sample = next((s for s in samples if s.well == well), None)
                
                if sample:
                    row_data.append(1)  # 1 = occupied
                    annotations.append(
                        dict(
                            x=c,
                            y=r,
                            text=sample.sample_name[:10],
                            showarrow=False,
                            font=dict(size=8)
                        )
                    )
                else:
                    row_data.append(0)  # 0 = empty
            
            heatmap_data.append(row_data)
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data,
            x=[f"{c+1}" for c in range(box.columns)],
            y=[chr(65 + r) for r in range(box.rows)],
            colorscale=[[0, 'white'], [1, 'green']],
            showscale=False
        ))
        
        fig.update_layout(
            title=f"Sample Density in Box {box.box_name or box.id}",
            xaxis_title="Column",
            yaxis_title="Row",
            annotations=annotations
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display sample list
        if samples:
            st.subheader(f"Samples in Box {box.box_name or box.id}")
            
            sample_data = []
            for sample in samples:
                sample_data.append({
                    'Well': sample.well,
                    'Sample Name': sample.sample_name,
                    'Type': sample.sample_type,
                    'Owner': sample.owner,
                    'Date Added': sample.date_added.strftime('%Y-%m-%d') if sample.date_added else ''
                })
            
            df_samples = pd.DataFrame(sample_data)
            st.dataframe(df_samples, use_container_width=True)
        else:
            st.info(f"No samples found in box {box.box_name or box.id}.")

def display_species_distribution():
    """Display species distribution analysis"""
    with get_db_session() as session:
        # Get species data
        species_data = session.query(
            Sample.species,
            Sample.sample_type,
            func.count(Sample.id).label('count')
        ).filter(
            Sample.species != '',
            Sample.species.isnot(None)
        ).group_by(Sample.species, Sample.sample_type).all()
        
        if not species_data:
            st.warning("No species data available for analysis.")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(species_data, columns=['Species', 'Sample Type', 'Count'])
        
        # Create visualization
        fig = px.treemap(
            df,
            path=['Sample Type', 'Species'],
            values='Count',
            title='Species Distribution by Sample Type',
            color='Count',
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Species bar chart
        species_summary = df.groupby('Species')['Count'].sum().reset_index()
        species_summary = species_summary.sort_values('Count', ascending=False)
        
        # Limit to top 15 species for readability
        if len(species_summary) > 15:
            other_count = species_summary.iloc[15:]['Count'].sum()
            species_summary = species_summary.iloc[:15]
            species_summary = pd.concat([
                species_summary, 
                pd.DataFrame([{'Species': 'Other', 'Count': other_count}])
            ])
        
        fig = px.bar(
            species_summary,
            x='Species',
            y='Count',
            title='Top Species Distribution',
            color='Count',
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig, use_container_width=True)