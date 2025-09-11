import pandas as pd
import os
from pathlib import Path

def load_participant_data(file_path):
    """
    Load participant data from CSV or Excel file.
    
    Args:
        file_path (str): Path to the participant data file
        
    Returns:
        dict: Dictionary with participant data and metadata
    """
    if not os.path.exists(file_path):
        return {'error': f'File not found: {file_path}', 'data': None}
    
    try:
        # Determine file type and load accordingly
        file_extension = Path(file_path).suffix.lower()
        
        if file_extension == '.csv':
            df = pd.read_csv(file_path)
        elif file_extension in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        else:
            return {'error': f'Unsupported file type: {file_extension}', 'data': None}
        
        # Basic validation
        if df.empty:
            return {'error': 'File is empty', 'data': None}
        
        result = {
            'data': df,
            'columns': df.columns.tolist(),
            'row_count': len(df),
            'file_path': file_path,
            'file_type': file_extension
        }
        
        # Try to identify key columns
        result['key_columns'] = identify_key_columns(df.columns.tolist())
        
        print(f"Loaded participant data: {len(df)} rows, {len(df.columns)} columns")
        print(f"Columns: {df.columns.tolist()}")
        
        return result
        
    except Exception as e:
        return {'error': f'Error loading file: {str(e)}', 'data': None}

def identify_key_columns(columns):
    """
    Try to automatically identify key columns in the participant data.
    
    Args:
        columns (list): List of column names
        
    Returns:
        dict: Dictionary mapping key types to column names
    """
    key_columns = {}
    
    # Convert to lowercase for easier matching
    lower_columns = [col.lower() for col in columns]
    
    # Common patterns for different types of columns
    patterns = {
        'participant_id': ['participant_id', 'subject_id', 'subject', 'sub', 'id', 'participant'],
        'name': ['name', 'full_name', 'participant_name', 'subject_name'],
        'first_name': ['first_name', 'firstname', 'given_name'],
        'last_name': ['last_name', 'lastname', 'surname', 'family_name'],
        'age': ['age', 'age_at_scan', 'age_years'],
        'sex': ['sex', 'gender'],
        'diagnosis': ['diagnosis', 'condition', 'group', 'status'],
        'date_of_birth': ['dob', 'date_of_birth', 'birth_date'],
        'scan_date': ['scan_date', 'date_scan', 'session_date']
    }
    
    # Try to match patterns
    for key_type, pattern_list in patterns.items():
        for pattern in pattern_list:
            if pattern in lower_columns:
                # Get the original column name (with correct case)
                original_index = lower_columns.index(pattern)
                key_columns[key_type] = columns[original_index]
                break
    
    return key_columns

def find_participant_by_name(participant_data, name_query):
    """
    Search for participants by name (partial matching).
    
    Args:
        participant_data (dict): Output from load_participant_data()
        name_query (str): Name to search for (can be partial)
        
    Returns:
        list: List of matching participant records
    """
    if participant_data.get('data') is None:
        return []
    
    df = participant_data['data']
    key_columns = participant_data['key_columns']
    
    # Convert search term to lowercase for case-insensitive search
    name_query = name_query.lower().strip()
    
    # Search in different name columns
    search_columns = []
    for name_type in ['name', 'first_name', 'last_name']:
        if name_type in key_columns:
            search_columns.append(key_columns[name_type])
    
    if not search_columns:
        # Fallback: search in all columns that might contain names
        potential_name_cols = [col for col in df.columns 
                              if any(name_word in col.lower() 
                                   for name_word in ['name', 'participant', 'subject'])]
        search_columns = potential_name_cols
    
    matches = []
    
    for _, row in df.iterrows():
        for col in search_columns:
            if col in row and pd.notna(row[col]):
                cell_value = str(row[col]).lower()
                if name_query in cell_value:
                    matches.append(row.to_dict())
                    break  # Avoid duplicate matches from same row
    
    return matches

def get_participant_id(participant_record, participant_data):
    """
    Extract the participant/subject ID from a participant record.
    
    Args:
        participant_record (dict): Single participant record
        participant_data (dict): Participant data metadata
        
    Returns:
        str or None: The participant ID
    """
    key_columns = participant_data.get('key_columns', {})
    
    # Try to get participant ID from identified key column
    if 'participant_id' in key_columns:
        id_col = key_columns['participant_id']
        return participant_record.get(id_col)
    
    # Fallback: search for columns that might contain IDs
    for key, value in participant_record.items():
        key_lower = key.lower()
        if any(id_term in key_lower for id_term in ['id', 'subject', 'participant']):
            return value
    
    return None

def find_participant_by_id(participant_data, participant_id):
    """
    Find a participant by their ID.
    """
    if participant_data.get('data') is None:
        return None
    df = participant_data['data']
    key_columns = participant_data['key_columns']
    # Clean the ID for comparison
    participant_id = str(participant_id).strip()
    # Try the identified participant ID column first
    if 'participant_id' in key_columns:
        id_col = key_columns['participant_id']
        matches = df[df[id_col].astype(str).str.strip() == participant_id]
        if not matches.empty:
            return matches.iloc[0].to_dict()
    # Fallback: search in any column that looks like an ID
    for col in df.columns:
        if any(id_term in col.lower() for id_term in ['id', 'subject', 'participant']):
            matches = df[df[col].astype(str).str.strip() == participant_id]
            if not matches.empty:
                return matches.iloc[0].to_dict()
    # If not found, try alternate forms with/without 'sub-' prefix
    alt_id_nosub = participant_id.lower().replace('sub-', '')
    alt_id_withsub = 'sub-' + alt_id_nosub
    if 'participant_id' in key_columns:
        id_col = key_columns['participant_id']
        matches = df[df[id_col].astype(str).str.strip().str.lower() == alt_id_withsub]
        if matches.empty:
            matches = df[df[id_col].astype(str).str.strip().str.lower() == alt_id_nosub]
        if not matches.empty:
            return matches.iloc[0].to_dict()
    for col in df.columns:
        if any(id_term in col.lower() for id_term in ['id', 'subject', 'participant']):
            matches = df[df[col].astype(str).str.strip().str.lower() == alt_id_withsub]
            if matches.empty:
                matches = df[df[col].astype(str).str.strip().str.lower() == alt_id_nosub]
            if not matches.empty:
                return matches.iloc[0].to_dict()
    return None

def filter_participants_by_criteria(participant_data, **criteria):
    """
    Filter participants based on criteria (e.g., age>60, sex='F').
    """
    if participant_data.get('data') is None:
        return []
    df = participant_data['data'].copy()
    for criterion, value in criteria.items():
        if criterion in df.columns:
            # inside filter_participants_by_criteria(...) where text columns are handled
            if criterion.lower() in ['sex', 'gender', 'sexo', 'género', 'genero']:
                df = df[df[criterion].astype(str).str.strip().str.casefold()
                        == str(value).strip().casefold()]
            else:
                # keep your existing behavior (contains) for other free-text fields
                df = df[df[criterion].astype(str).str.contains(str(value), case=False, na=False)]

            if isinstance(value, str) and any(op in value for op in ['>', '<', '>=', '<=', '!=']):
                # Numeric comparisons on DataFrame
                try:
                    if '>=' in value:
                        threshold = float(value.replace('>=', '').strip()); df = df[df[criterion] >= threshold]
                    elif '>' in value:
                        threshold = float(value.replace('>', '').strip()); df = df[df[criterion] > threshold]
                    elif '<=' in value:
                        threshold = float(value.replace('<=', '').strip()); df = df[df[criterion] <= threshold]
                    elif '<' in value:
                        threshold = float(value.replace('<', '').strip()); df = df[df[criterion] < threshold]
                    elif '!=' in value:
                        not_val = value.replace('!=', '').strip(); df = df[df[criterion] != not_val]
                except ValueError:
                    print(f"Warning: Could not parse numerical criterion: {criterion}={value}")
                    
            else:
                # Tolerant matching for other criteria
                if pd.api.types.is_numeric_dtype(df[criterion]):
                    try:
                        num_val = float(value)
                        df = df[df[criterion] == num_val]
                    except:
                        df = df[df[criterion].astype(str) == str(value)]
                else:
                    df = df[df[criterion].astype(str).str.contains(str(value), case=False, na=False)]
        else:
            print(f"Warning: Column '{criterion}' not found in participant data")
    return df.to_dict('records')


def get_participant_summary(participant_data):
    """
    Get a summary of the participant data.
    
    Args:
        participant_data (dict): Output from load_participant_data()
        
    Returns:
        dict: Summary information
    """
    if participant_data.get('data') is None:
        return {'error': 'No participant data available'}
    
    df = participant_data['data']
    key_columns = participant_data['key_columns']
    
    summary = {
        'total_participants': len(df),
        'columns': df.columns.tolist(),
        'key_columns': key_columns,
        'sample_data': df.head(3).to_dict('records')  # First 3 rows as example
    }
    
    # Add statistics for numerical columns
    numerical_stats = {}
    for col in df.select_dtypes(include=['number']).columns:
        numerical_stats[col] = {
            'min': float(df[col].min()),
            'max': float(df[col].max()),
            'mean': float(df[col].mean())
        }
    
    if numerical_stats:
        summary['numerical_stats'] = numerical_stats
    
    return summary

# Test function
if __name__ == '__main__':
    # Example usage - replace with actual file path
    file_path = "participants.csv"
    
    if os.path.exists(file_path):
        participant_data = load_participant_data(file_path)
        
        if 'error' not in participant_data:
            print("Participant data loaded successfully!")
            summary = get_participant_summary(participant_data)
            print(f"Total participants: {summary['total_participants']}")
            print(f"Key columns identified: {summary['key_columns']}")
            
            # Test search functionality
            matches = find_participant_by_name(participant_data, "john")
            print(f"Matches for 'john': {len(matches)}")
        else:
            print(f"Error: {participant_data['error']}")
    else:
        print(f"Test file not found: {file_path}")