import re
import pandas as pd
from db_utils import get_db_session
from model import Sample, Box

class ValidationError(Exception):
    """Exception raised for validation errors"""
    pass

def validate_well_format(well):
    """
    Validate that a well position is in the correct format (e.g., A1, B12)
    
    Parameters:
    - well: The well position to validate
    
    Returns:
    - True if valid, raises ValidationError if invalid
    """
    if not well:
        raise ValidationError("Well position cannot be empty")
    
    # Well format should be a letter followed by a number (e.g., A1, B12)
    pattern = r'^[A-Z][0-9]{1,2}$'
    if not re.match(pattern, well):
        raise ValidationError(f"Well position '{well}' is invalid. Format should be a letter followed by a number (e.g., A1, B12)")
    
    return True

def validate_well_in_box(well, box_rows, box_cols):
    """
    Validate that a well position is within the box dimensions
    
    Parameters:
    - well: The well position to validate
    - box_rows: Number of rows in the box
    - box_cols: Number of columns in the box
    
    Returns:
    - True if valid, raises ValidationError if invalid
    """
    if not well:
        raise ValidationError("Well position cannot be empty")
    
    # Extract row letter and column number
    row_letter = well[0]
    col_number = int(well[1:])
    
    # Convert row letter to index (A=0, B=1, etc.)
    row_index = ord(row_letter) - ord('A')
    
    # Check if row and column are within box dimensions
    if row_index < 0 or row_index >= box_rows:
        raise ValidationError(f"Row '{row_letter}' is outside the box dimensions (max row: {chr(ord('A') + box_rows - 1)})")
    
    if col_number < 1 or col_number > box_cols:
        raise ValidationError(f"Column '{col_number}' is outside the box dimensions (max column: {box_cols})")
    
    return True

def validate_sample_name(sample_name):
    """
    Validate that a sample name is not empty and has a reasonable length
    
    Parameters:
    - sample_name: The sample name to validate
    
    Returns:
    - True if valid, raises ValidationError if invalid
    """
    if not sample_name:
        raise ValidationError("Sample name cannot be empty")
    
    if len(sample_name) > 100:
        raise ValidationError(f"Sample name is too long ({len(sample_name)} characters). Maximum length is 100 characters")
    
    return True

def validate_sample_type(sample_type, allowed_types=None):
    """
    Validate that a sample type is in the list of allowed types
    
    Parameters:
    - sample_type: The sample type to validate
    - allowed_types: List of allowed sample types (default: ["Cell Line", "DNA", "RNA", "Protein", "Other"])
    
    Returns:
    - True if valid, raises ValidationError if invalid
    """
    if allowed_types is None:
        allowed_types = ["Cell Line", "DNA", "RNA", "Protein", "Other"]
    
    if not sample_type:
        raise ValidationError("Sample type cannot be empty")
    
    if sample_type not in allowed_types:
        raise ValidationError(f"Sample type '{sample_type}' is not valid. Allowed types: {', '.join(allowed_types)}")
    
    return True

def validate_unique_sample(freezer, rack, box, well, sample_id=None):
    """
    Validate that a sample is unique in the given location
    
    Parameters:
    - freezer: Freezer name
    - rack: Rack ID
    - box: Box ID
    - well: Well position
    - sample_id: ID of the current sample (for updates, to exclude from uniqueness check)
    
    Returns:
    - True if valid, raises ValidationError if invalid
    """
    with get_db_session() as session:
        query = session.query(Sample).filter_by(
            freezer=freezer,
            rack=rack,
            box=box,
            well=well
        )
        
        if sample_id is not None:
            query = query.filter(Sample.id != sample_id)
        
        existing_sample = query.first()
        
        if existing_sample:
            raise ValidationError(f"A sample already exists at location {freezer}/{rack}/{box}/{well} (Sample: {existing_sample.sample_name})")
    
    return True

def validate_sample_form(freezer, rack, box, well, sample_name, sample_type, sample_id=None):
    """
    Validate all sample form fields
    
    Parameters:
    - freezer: Freezer name
    - rack: Rack ID
    - box: Box ID
    - well: Well position
    - sample_name: Sample name
    - sample_type: Sample type
    - sample_id: ID of the current sample (for updates)
    
    Returns:
    - True if all validations pass, raises ValidationError if any validation fails
    """
    # Get box dimensions
    with get_db_session() as session:
        box_info = session.query(Box).filter_by(
            freezer_name=freezer,
            rack_id=rack,
            id=box
        ).first()
        
        if not box_info:
            raise ValidationError(f"Box {box} not found in rack {rack} of freezer {freezer}")
        
        box_rows = box_info.rows
        box_cols = box_info.columns
    
    # Validate all fields
    validate_well_format(well)
    validate_well_in_box(well, box_rows, box_cols)
    validate_sample_name(sample_name)
    validate_sample_type(sample_type)
    validate_unique_sample(freezer, rack, box, well, sample_id)
    
    return True

def validate_csv_upload(df, freezer, rack, box):
    """
    Validate a CSV upload for bulk sample import
    
    Parameters:
    - df: Pandas DataFrame with sample data
    - freezer: Freezer name
    - rack: Rack ID
    - box: Box ID
    
    Returns:
    - Tuple of (is_valid, errors) where is_valid is a boolean and errors is a list of error messages
    """
    errors = []
    
    # Get box dimensions
    with get_db_session() as session:
        box_info = session.query(Box).filter_by(
            freezer_name=freezer,
            rack_id=rack,
            id=box
        ).first()
        
        if not box_info:
            errors.append(f"Box {box} not found in rack {rack} of freezer {freezer}")
            return False, errors
        
        box_rows = box_info.rows
        box_cols = box_info.columns
    
    # Check required columns
    required_columns = ["freezer", "rack", "box", "well", "sample_name", "sample_type"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        errors.append(f"Missing required columns: {', '.join(missing_columns)}")
        return False, errors
    
    # Validate each row
    for i, row in df.iterrows():
        # Skip empty rows or rows with empty sample names
        if pd.isna(row["sample_name"]) or str(row["sample_name"]).strip() == "":
            continue
        
        try:
            # Validate well format and dimensions
            well = row["well"]
            validate_well_format(well)
            validate_well_in_box(well, box_rows, box_cols)
            
            # Validate sample name and type
            sample_name = row["sample_name"]
            sample_type = row["sample_type"]
            validate_sample_name(sample_name)
            validate_sample_type(sample_type)
            
        except ValidationError as e:
            errors.append(f"Row {i+1}: {str(e)}")
    
    # Check for duplicate wells in the CSV
    well_counts = df["well"].value_counts()
    duplicate_wells = well_counts[well_counts > 1].index.tolist()
    
    if duplicate_wells:
        errors.append(f"Duplicate wells in CSV: {', '.join(duplicate_wells)}")
    
    return len(errors) == 0, errors

def sanitize_input(input_str):
    """
    Sanitize user input to prevent injection attacks
    
    Parameters:
    - input_str: The input string to sanitize
    
    Returns:
    - Sanitized string
    """
    if input_str is None:
        return None
    
    # Convert to string if not already
    input_str = str(input_str)
    
    # Remove any HTML/script tags
    input_str = re.sub(r'<[^>]*>', '', input_str)
    
    # Remove any SQL injection patterns
    input_str = re.sub(r'[\'";]', '', input_str)
    
    return input_str.strip()