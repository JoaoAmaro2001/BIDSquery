import re
import pandas as pd
from bids_manager import discover_bids_datasets, find_subject_files_all_datasets, query_bids_files
from participant_manager import (find_participant_by_name, get_participant_id, 
                                find_participant_by_id, filter_participants_by_criteria)

def _clean_participant_record(participant_record):
    """
    Remove empty, NaN, NaT, or useless values from participant record.
    
    Args:
        participant_record (dict): Raw participant record
        
    Returns:
        dict: Cleaned participant record with only meaningful values
    """
    if not isinstance(participant_record, dict):
        return {}
    
    cleaned = {}
    for key, value in participant_record.items():
        # Skip if value is None
        if value is None:
            continue
            
        # Convert pandas NaN/NaT to None and skip
        if pd.isna(value):
            continue
            
        # Skip empty strings
        if isinstance(value, str) and value.strip() == "":
            continue
            
        # Keep the value if it has meaningful content
        cleaned[key] = value
    
    return cleaned

def query_by_participant_name(name_query, base_dir, participant_data):
    """
    Find BIDS files for participants matching a name query.
    
    This is the "sensitive info → BIDS files" direction.
    
    Args:
        name_query (str): Name to search for
        base_dir (str): Base directory containing studies
        participant_data (dict): Loaded participant data
        
    Returns:
        dict: Query results with participant matches and their BIDS files
    """
    results = {
        'query_type': 'by_name',
        'query': name_query,
        'participants_found': [],
        'files_found': [],
        'total_files': 0,
        'datasets_searched': []
    }
    
    # Step 1: Find participants matching the name
    participant_matches = find_participant_by_name(participant_data, name_query)
    
    if not participant_matches:
        results['error'] = f"No participants found matching '{name_query}'"
        return results
    
    # Clean participant records (remove empty values)
    cleaned_participants = []
    for participant in participant_matches:
        cleaned = _clean_participant_record(participant)
        if cleaned:  # Only add if there's meaningful data
            cleaned_participants.append(cleaned)
    
    results['participants_found'] = cleaned_participants
    
    # Step 2: Discover BIDS datasets
    datasets = discover_bids_datasets(base_dir)
    results['datasets_searched'] = [d['path'] for d in datasets]
    
    if not datasets:
        results['error'] = "No BIDS datasets found in the specified directory"
        return results
    
    # Step 3: For each matching participant, find their BIDS files
    for participant in cleaned_participants:
        participant_id = get_participant_id(participant, participant_data)
        
        if not participant_id:
            print(f"Warning: Could not determine participant ID for {participant}")
            continue
        
        # Remove 'sub-' prefix if present for BIDS search
        search_id = participant_id.replace('sub-', '') if participant_id.startswith('sub-') else participant_id
        
        # Find files across all datasets
        participant_files = find_subject_files_all_datasets(search_id, datasets)
        
        # Add cleaned participant info to each file record
        for file_info in participant_files:
            file_info['participant_info'] = participant
            file_info['participant_id'] = participant_id
            results['files_found'].append(file_info)
    
    results['total_files'] = len(results['files_found'])
    
    # Group files by participant for easier display
    results['files_by_participant'] = {}
    for file_info in results['files_found']:
        pid = file_info['participant_id']
        if pid not in results['files_by_participant']:
            results['files_by_participant'][pid] = []
        results['files_by_participant'][pid].append(file_info)
    
    return results

def query_by_bids_criteria(base_dir, participant_data, **criteria):
    """
    Find participants whose BIDS files match specific criteria.
    
    This is the "BIDS criteria → participants" direction.
    
    Args:
        base_dir (str): Base directory containing studies
        participant_data (dict): Loaded participant data
        **criteria: BIDS query criteria (e.g., datatype='anat', suffix='T1w', age='>60')
        
    Returns:
        dict: Query results with matching files and participant information
    """
    results = {
        'query_type': 'by_criteria',
        'criteria': criteria,
        'files_found': [],
        'participants_found': [],
        'total_files': 0,
        'datasets_searched': []
    }
    
    print(f"DEBUG: Starting criteria search with: {criteria}")
    
    # Separate BIDS criteria from participant criteria
    bids_criteria = {}
    participant_criteria = {}
    
    for key, value in criteria.items():
        if key in ['datatype', 'suffix', 'extension', 'task', 'session', 'run', 'acquisition']:
            bids_criteria[key] = value
        else:
            participant_criteria[key] = value
    
    print(f"DEBUG: BIDS criteria: {bids_criteria}")
    print(f"DEBUG: Participant criteria: {participant_criteria}")
    
    # Step 1: Discover BIDS datasets
    datasets = discover_bids_datasets(base_dir)
    results['datasets_searched'] = [d['path'] for d in datasets]
    
    if not datasets:
        results['error'] = "No BIDS datasets found in the specified directory"
        return results
    
    print(f"DEBUG: Found {len(datasets)} datasets")
    
    # Step 2: Handle participant criteria first if no BIDS criteria
    if participant_criteria and not bids_criteria:
        print("DEBUG: Filtering by participant criteria only")
        # Filter participants first, then get all their files
        try:
            filtered_participants = filter_participants_by_criteria(participant_data, **participant_criteria)
            print(f"DEBUG: Found {len(filtered_participants)} participants matching criteria")
            
            if not filtered_participants:
                results['error'] = "No participants found matching the specified criteria"
                return results
            
            # Clean participant records
            cleaned_participants = []
            for participant in filtered_participants:
                cleaned = _clean_participant_record(participant)
                if cleaned:
                    cleaned_participants.append(cleaned)
            
            results['participants_found'] = cleaned_participants
            
            # Get all files for these participants
            all_files = []
            for participant in cleaned_participants:
                participant_id = get_participant_id(participant, participant_data)
                if participant_id:
                    search_id = participant_id.replace('sub-', '') if participant_id.startswith('sub-') else participant_id
                    participant_files = find_subject_files_all_datasets(search_id, datasets)
                    
                    for file_info in participant_files:
                        file_info['participant_info'] = participant
                        file_info['participant_id'] = participant_id
                        all_files.append(file_info)
            
            results['files_found'] = all_files
            results['total_files'] = len(all_files)
            return results
            
        except Exception as e:
            print(f"DEBUG: Error in participant filtering: {e}")
            results['error'] = f"Error filtering participants: {e}"
            return results
    
    # Step 3: Query BIDS files based on criteria
    matching_files = []
    if bids_criteria:
        print(f"DEBUG: Querying BIDS files with criteria: {bids_criteria}")
        try:
            matching_files = query_bids_files(datasets, **bids_criteria)
            print(f"DEBUG: Found {len(matching_files)} files matching BIDS criteria")
        except Exception as e:
            print(f"DEBUG: Error querying BIDS files: {e}")
            results['error'] = f"Error querying BIDS files: {e}"
            return results
    else:
        # If no BIDS criteria, get all files from all datasets
        print("DEBUG: No BIDS criteria, getting all files")
        for dataset in datasets:
            try:
                dataset_files = query_bids_files([dataset])
                matching_files.extend(dataset_files)
            except Exception as e:
                print(f"DEBUG: Error getting files from dataset {dataset['path']}: {e}")
                continue
    
    print(f"DEBUG: Total files before participant filtering: {len(matching_files)}")
    
    # Step 4: Extract subject IDs from matching files and get participant info
    subject_ids = set()
    for file_info in matching_files:
        # Extract subject ID from file path or entities
        file_subject_id = None
        if 'entities' in file_info and 'subject' in file_info['entities']:
            file_subject_id = file_info['entities']['subject']
        else:
            # Try to extract from file path
            match = re.search(r'/sub-([^/]+)/', file_info['path'])
            if match:
                file_subject_id = match.group(1)
        
        if file_subject_id:
            subject_ids.add(file_subject_id)
    
    print(f"DEBUG: Found {len(subject_ids)} unique subject IDs: {list(subject_ids)[:10]}...")  # Show first 10
    
    # Step 5: Get participant information for each subject
    participants_with_info = []
    for subject_id in subject_ids:
        participant_record = find_participant_by_id(participant_data, subject_id)
        if participant_record:
            cleaned_participant = _clean_participant_record(participant_record)
            if cleaned_participant:
                participants_with_info.append(cleaned_participant)
    
    print(f"DEBUG: Found participant info for {len(participants_with_info)} subjects")
    
    # Step 6: Apply participant criteria filters if any
    if participant_criteria:
        print(f"DEBUG: Applying participant criteria: {participant_criteria}")
        filtered_participants = []
        for participant in participants_with_info:
            matches_criteria = True
            for criterion, value in participant_criteria.items():
                # Check if criterion exists in participant data
                criterion_value = None
                
                # Try exact match first
                if criterion in participant:
                    criterion_value = participant[criterion]
                else:
                    # Try case-insensitive match
                    for key in participant.keys():
                        if key.lower() == criterion.lower():
                            criterion_value = participant[key]
                            break
                
                if criterion_value is None:
                    print(f"DEBUG: Criterion '{criterion}' not found in participant data. Available keys: {list(participant.keys())}")
                    matches_criteria = False
                    break
                
                # Apply the filter
                if not _matches_criterion(criterion_value, value):
                    matches_criteria = False
                    break
            
            if matches_criteria:
                filtered_participants.append(participant)
        
        print(f"DEBUG: After participant criteria filtering: {len(filtered_participants)} participants")
        participants_with_info = filtered_participants
        
        # Filter files to include only those belonging to matching participants
        if participants_with_info:
            matching_subject_ids = set()
            for p in participants_with_info:
                pid = get_participant_id(p, participant_data)
                if pid:
                    # Normalize ID by removing 'sub-' if present
                    matching_subject_ids.add(pid.replace('sub-', '') if pid.startswith('sub-') else pid)
            
            print(f"DEBUG: Matching subject IDs after filtering: {matching_subject_ids}")
            
            filtered_files = []
            for file_info in matching_files:
                file_subject_id = None
                if 'entities' in file_info and 'subject' in file_info['entities']:
                    file_subject_id = file_info['entities']['subject']
                else:
                    match = re.search(r'/sub-([^/]+)/', file_info['path'])
                    if match:
                        file_subject_id = match.group(1)
                
                if file_subject_id in matching_subject_ids:
                    filtered_files.append(file_info)
            
            matching_files = filtered_files
            print(f"DEBUG: Files after participant filtering: {len(matching_files)}")
    
    results['files_found'] = matching_files
    results['total_files'] = len(matching_files)
    results['participants_found'] = participants_with_info

    # Add participant info to file records
    participant_lookup = {}
    for p in participants_with_info:
        pid = get_participant_id(p, participant_data)
        if pid:
            participant_lookup[pid] = p
            # Also add normalized version
            normalized_pid = pid.replace('sub-', '') if pid.startswith('sub-') else pid
            participant_lookup[normalized_pid] = p
    
    for file_info in results['files_found']:
        file_subject_id = None
        if 'entities' in file_info and 'subject' in file_info['entities']:
            file_subject_id = file_info['entities']['subject']
        else:
            match = re.search(r'/sub-([^/]+)/', file_info['path'])
            if match:
                file_subject_id = match.group(1)
        
        # Look for participant info
        if file_subject_id and file_subject_id in participant_lookup:
            file_info['participant_info'] = participant_lookup[file_subject_id]
    
    print(f"DEBUG: Final results: {len(results['participants_found'])} participants, {results['total_files']} files")
    return results

def _matches_criterion(participant_value, criterion_value):
    """
    Check if a participant value matches a criterion.
    
    Args:
        participant_value: Value from participant data
        criterion_value: Value to match against
        
    Returns:
        bool: True if matches, False otherwise
    """
    try:
        # Handle comparison operators for numeric values
        if isinstance(criterion_value, str) and any(op in criterion_value for op in ['>=', '<=', '>', '<', '!=']):
            try:
                # Convert participant value to float for numeric comparison
                participant_num = float(participant_value)
                
                if '>=' in criterion_value:
                    threshold = float(criterion_value.replace('>=', '').strip())
                    return participant_num >= threshold
                elif '>' in criterion_value:
                    threshold = float(criterion_value.replace('>', '').strip())
                    return participant_num > threshold
                elif '<=' in criterion_value:
                    threshold = float(criterion_value.replace('<=', '').strip())
                    return participant_num <= threshold
                elif '<' in criterion_value:
                    threshold = float(criterion_value.replace('<', '').strip())
                    return participant_num < threshold
                elif '!=' in criterion_value:
                    not_value = criterion_value.replace('!=', '').strip()
                    try:
                        not_value_num = float(not_value)
                        return participant_num != not_value_num
                    except ValueError:
                        return str(participant_value).strip() != not_value
            except (ValueError, TypeError):
                # If can't convert to numbers, treat as string comparison
                return False
        
        # Handle exact or fuzzy text matching
        else:
            # Try numeric equality first
            try:
                return float(participant_value) == float(criterion_value)
            except (ValueError, TypeError):
                # Fall back to case-insensitive substring match
                participant_str = str(participant_value).lower().strip()
                criterion_str = str(criterion_value).lower().strip()
                return criterion_str in participant_str
    
    except Exception as e:
        print(f"DEBUG: Error matching criterion: {e}")
        return False

def get_datasets_summary(base_dir):
    """
    Get a summary of all BIDS datasets in the base directory.
    
    Args:
        base_dir (str): Base directory containing studies
        
    Returns:
        dict: Summary information about available datasets
    """
    datasets = discover_bids_datasets(base_dir)
    
    summary = {
        'total_datasets': len(datasets),
        'datasets': []
    }
    
    for dataset in datasets:
        from bids_manager import get_dataset_info
        info = get_dataset_info(dataset['path'])
        
        dataset_summary = {
            'name': dataset['name'],
            'path': dataset['path'],
            'project_folder': dataset['project_folder'],
            'subjects_count': len(info['subjects']),
            'datatypes': info['datatypes'],
            'sessions_count': len(info['sessions']) if info['sessions'] else 0,
        }
        
        summary['datasets'].append(dataset_summary)
    
    return summary