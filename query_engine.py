from bids_manager import discover_bids_datasets, find_subject_files_all_datasets, query_bids_files
from participant_manager import (find_participant_by_name, get_participant_id, 
                                find_participant_by_id, filter_participants_by_criteria)

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
    
    results['participants_found'] = participant_matches
    
    # Step 2: Discover BIDS datasets
    datasets = discover_bids_datasets(base_dir)
    results['datasets_searched'] = [d['path'] for d in datasets]
    
    if not datasets:
        results['error'] = "No BIDS datasets found in the specified directory"
        return results
    
    # Step 3: For each matching participant, find their BIDS files
    for participant in participant_matches:
        participant_id = get_participant_id(participant, participant_data)
        
        if not participant_id:
            print(f"Warning: Could not determine participant ID for {participant}")
            continue
        
        # Remove 'sub-' prefix if present for BIDS search
        search_id = participant_id.replace('sub-', '') if participant_id.startswith('sub-') else participant_id
        
        # Find files across all datasets
        participant_files = find_subject_files_all_datasets(search_id, datasets)
        
        # Add participant info to each file record
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
    
    # Separate BIDS criteria from participant criteria
    bids_criteria = {}
    participant_criteria = {}
    
    for key, value in criteria.items():
        if key in ['datatype', 'suffix', 'extension', 'task', 'session', 'run', 'acquisition']:
            bids_criteria[key] = value
        else:
            participant_criteria[key] = value
    
    # Step 1: Discover BIDS datasets
    datasets = discover_bids_datasets(base_dir)
    results['datasets_searched'] = [d['path'] for d in datasets]
    
    if not datasets:
        results['error'] = "No BIDS datasets found in the specified directory"
        return results
    
    # Step 2: Query BIDS files based on criteria
    if bids_criteria:
        matching_files = query_bids_files(datasets, **bids_criteria)
    else:
        # If no BIDS criteria, we'll filter by participant criteria only
        matching_files = []
        # Get all files from all datasets
        for dataset in datasets:
            all_files = query_bids_files([dataset])
            matching_files.extend(all_files)
    
    results['files_found'] = matching_files
    results['total_files'] = len(matching_files)
    
    # Step 3: Extract subject IDs from matching files and get participant info
    subject_ids = set()
    for file_info in matching_files:
        # Extract subject ID from file path or entities
        if 'entities' in file_info and 'subject' in file_info['entities']:
            subject_ids.add(file_info['entities']['subject'])
        else:
            # Try to extract from file path
            import re
            match = re.search(r'/sub-([^/]+)/', file_info['path'])
            if match:
                subject_ids.add(match.group(1))
    
    # Step 4: Get participant information for each subject
    participants_with_info = []
    for subject_id in subject_ids:
        participant_record = find_participant_by_id(participant_data, subject_id)
        if participant_record:
            participants_with_info.append(participant_record)
    # Step 5: Apply participant criteria filters
    if participant_criteria:
        filtered_participants = []
        for participant in participants_with_info:
            matches_criteria = True
            for criterion, value in participant_criteria.items():
                if criterion not in participant:
                    matches_criteria = False
                    break
                if isinstance(value, str) and any(op in value for op in ['>', '<', '>=', '<=', '!=']):
                    # Handle numeric comparisons
                    try:
                        participant_value = float(participant[criterion])
                        if '>=' in value:
                            threshold = float(value.replace('>=', '').strip())
                            if not participant_value >= threshold:
                                matches_criteria = False
                        elif '>' in value:
                            threshold = float(value.replace('>', '').strip())
                            if not participant_value > threshold:
                                matches_criteria = False
                        elif '<=' in value:
                            threshold = float(value.replace('<=', '').strip())
                            if not participant_value <= threshold:
                                matches_criteria = False
                        elif '<' in value:
                            threshold = float(value.replace('<', '').strip())
                            if not participant_value < threshold:
                                matches_criteria = False
                        elif '!=' in value:
                            not_value = value.replace('!=', '').strip()
                            if str(participant_value) == not_value:
                                matches_criteria = False
                    except (ValueError, KeyError):
                        matches_criteria = False
                else:
                    # Fuzzy matching for non-comparison criteria
                    try:
                        # If both values are numeric, compare as numbers
                        if float(participant[criterion]) == float(value):
                            # numeric equality match
                            pass
                        else:
                            matches_criteria = False
                    except:
                        # Case-insensitive substring match for text
                        if str(value).lower() not in str(participant[criterion]).lower():
                            matches_criteria = False
                if not matches_criteria:
                    break
            if matches_criteria:
                filtered_participants.append(participant)
        participants_with_info = filtered_participants
        # Filter files to include only those belonging to matching participants
        matching_subject_ids = set()
        for p in participants_with_info:
            pid = get_participant_id(p, participant_data)
            if pid:
                # Normalize ID by removing 'sub-' if present
                matching_subject_ids.add(pid.replace('sub-', '') if pid.startswith('sub-') else pid)
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
        results['files_found'] = filtered_files
        results['total_files'] = len(filtered_files)
    results['participants_found'] = participants_with_info

    # Add participant info to file records
    participant_lookup = {get_participant_id(p, participant_data): p for p in participants_with_info}
    
    for file_info in results['files_found']:
        file_subject_id = None
        if 'entities' in file_info and 'subject' in file_info['entities']:
            file_subject_id = file_info['entities']['subject']
        else:
            import re
            match = re.search(r'/sub-([^/]+)/', file_info['path'])
            if match:
                file_subject_id = match.group(1)
        
        # Look for participant info
        for pid, participant in participant_lookup.items():
            if pid and (pid == file_subject_id or pid == f"sub-{file_subject_id}"):
                file_info['participant_info'] = participant
                break
    
    return results

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

# # Test functions
# if __name__ == '__main__':
#     # Example usage - replace with actual paths
#     base_dir = "Z:\\"
#     participant_file = "C:\\github\\JoaoAmaro2001\\BIDSquery\\sensitive.xlsx"
    
#     print("This is a test of the query engine.")
#     print("Replace the paths above with real ones to test functionality.")
    
#     # Example queries you could run:
#     examples = [
#         "query_by_participant_name('john doe', base_dir, participant_data)",
#         "query_by_bids_criteria(base_dir, participant_data, datatype='anat', suffix='T1w')",
#         "query_by_bids_criteria(base_dir, participant_data, age='>60', datatype='func')"
#     ]
    
#     print("\nExample queries:")
#     for example in examples:
#         print(f"  {example}")