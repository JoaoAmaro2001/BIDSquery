import os
import json
from pathlib import Path
from bids.layout import BIDSLayout

# Global cache to store BIDSLayout objects
_layout_cache = {}

def discover_bids_datasets(base_dir, max_levels=3):
    """
    Discover BIDS datasets by locating directories named 'bids' (case-insensitive),
    searching only up to `max_levels` directory levels below `base_dir` for speed.

    For each study (defined as the parent directory of a 'bids' folder), select
    only the *most-upstream* 'bids' directory within that study and ignore any
    nested/duplicate 'bids' folders beneath it.

    Args:
        base_dir (str | Path): Root directory to search.
        max_levels (int): Maximum directory levels (relative to base_dir) to traverse.
                          Depth is counted by the number of path components:
                          base_dir has depth 0, base_dir/a -> 1, ..., etc.

    Returns:
        list[dict]: One entry per study with keys:
            - path (str): absolute path to the selected 'bids' directory
            - name (str): study folder name (parent of 'bids')
            - project_folder (str): absolute path to the parent of the study folder
            - description (dict): parsed dataset_description.json if available, else {}
    """
    base_path = Path(base_dir).resolve()
    datasets = []

    if not base_path.exists():
        print(f"Warning: Base directory does not exist: {base_path}")
        return datasets

    print(f"Scanning for 'bids' folders (depth ≤ {max_levels}) in: {base_path}")

    # 1) Collect ALL directories named 'bids' within the depth limit
    bids_dirs = []
    for root, dirs, _files in os.walk(base_path, topdown=True):
        # Compute depth of current root relative to base_dir
        rel = Path(root).resolve().relative_to(base_path)
        depth = len(rel.parts)  # base_dir => 0, base_dir/a => 1, ...

        # If we're already at or beyond the max depth, do not descend further
        if depth >= max_levels:
            dirs[:] = []  # prune traversal
            continue

        # Record any 'bids' dirs at this level (their depth would be depth+1 ≤ max_levels)
        for d in dirs:
            if d.lower() == "bids":
                bids_dirs.append((Path(root) / d).resolve())

    if not bids_dirs:
        print("No 'bids' folders found within the depth limit.")
        return datasets

    # 2) Sort by path depth (shallower first), then lexicographically
    bids_dirs = sorted(bids_dirs, key=lambda p: (len(p.parts), str(p)))

    # 3) Keep only the first (most-upstream) 'bids' per study (study = parent of 'bids')
    selected_study_roots = []  # Paths to study dirs already claimed

    for bids_dir in bids_dirs:
        study_dir = bids_dir.parent  # study is the parent of 'bids'

        # skip if this bids_dir is under a study we've already selected
        skip = any(bids_dir.is_relative_to(study_root) for study_root in selected_study_roots)
        if skip:
            continue

        # select this study root and build dataset info
        selected_study_roots.append(study_dir)

        dataset_info = {
            "path": str(bids_dir),
            "name": study_dir.name,                  # study folder name
            "project_folder": str(study_dir.parent), # parent of study
            "description": {}
        }

        # Optional: read dataset_description.json if available
        desc_file = bids_dir / "dataset_description.json"
        if desc_file.exists():
            try:
                with open(desc_file, "r", encoding="utf-8") as f:
                    dataset_info["description"] = json.load(f)
            except Exception as e:
                print(f"Warning: Could not read dataset_description for {bids_dir}: {e}")

        datasets.append(dataset_info)
        print(f"Found study: {dataset_info['name']}  ->  {dataset_info['path']}")

    print(f"Total studies (unique, most-upstream 'bids'): {len(datasets)}")
    return datasets


def get_bids_layout(dataset_path):
    """
    Get or create a BIDSLayout for the given dataset path.
    Uses caching to avoid recreating layouts.
    
    Args:
        dataset_path (str): Path to the BIDS dataset
        
    Returns:
        BIDSLayout or None: The BIDS layout object
    """
    if dataset_path in _layout_cache:
        return _layout_cache[dataset_path]
    
    try:
        print(f"Creating BIDS layout for: {dataset_path}")
        layout = BIDSLayout(dataset_path)
        _layout_cache[dataset_path] = layout
        return layout
    except Exception as e:
        print(f"Error creating BIDS layout for {dataset_path}: {e}")
        return None

def get_dataset_subjects(dataset_path):
    """
    Get all subject IDs from a BIDS dataset.
    
    Args:
        dataset_path (str): Path to the BIDS dataset
        
    Returns:
        list: List of subject IDs
    """
    layout = get_bids_layout(dataset_path)
    if layout is None:
        return []
    
    try:
        subjects = layout.get_subjects()
        return subjects
    except Exception as e:
        print(f"Error getting subjects from {dataset_path}: {e}")
        return []

def get_dataset_info(dataset_path):
    """
    Get comprehensive information about a BIDS dataset.
    
    Args:
        dataset_path (str): Path to the BIDS dataset
        
    Returns:
        dict: Dataset information including subjects, sessions, datatypes
    """
    layout = get_bids_layout(dataset_path)
    if layout is None:
        return {
            'path': dataset_path,
            'subjects': [],
            'sessions': [],
            'datatypes': [],
            'error': 'Could not create BIDS layout'
        }
    
    try:
        info = {
            'path': dataset_path,
            'subjects': layout.get_subjects(),
            'sessions': layout.get_sessions(),
            'datatypes': layout.get_datatypes(),
            'tasks': layout.get_tasks() if hasattr(layout, 'get_tasks') else []
        }
        return info
    except Exception as e:
        return {
            'path': dataset_path,
            'subjects': [],
            'sessions': [],
            'datatypes': [],
            'error': str(e)
        }

def find_subject_files_all_datasets(subject_id, datasets):
    """
    Find all files for a given subject across all BIDS datasets.
    
    Args:
        subject_id (str): The subject ID to search for
        datasets (list): List of dataset dictionaries from discover_bids_datasets()
        
    Returns:
        list: List of dictionaries containing file information
    """
    all_files = []
    
    for dataset in datasets:
        dataset_path = dataset['path']
        layout = get_bids_layout(dataset_path)
        
        if layout is None:
            continue
        
        try:
            # Get all files for this subject
            files = layout.get(subject=subject_id, return_type='filename')
            
            # Add dataset context to each file
            for file_path in files:
                file_info = {
                    'path': file_path,
                    'dataset': dataset_path,
                    'dataset_name': dataset['name'],
                    'project_folder': dataset['project_folder']
                }
                all_files.append(file_info)
        
        except Exception as e:
            print(f"Error searching for subject {subject_id} in {dataset_path}: {e}")
    
    return all_files

def query_bids_files(datasets, **criteria):
    """
    Query BIDS files across all datasets using specific criteria.
    
    Args:
        datasets (list): List of dataset dictionaries
        **criteria: BIDS query criteria (e.g., datatype='anat', suffix='T1w')
        
    Returns:
        list: List of file dictionaries matching the criteria
    """
    all_files = []
    
    for dataset in datasets:
        dataset_path = dataset['path']
        layout = get_bids_layout(dataset_path)
        
        if layout is None:
            continue
        
        try:
            # Query files using the provided criteria
            files = layout.get(return_type='filename', **criteria)
            
            # Add dataset context to each file
            for file_path in files:
                file_info = {
                    'path': file_path,
                    'dataset': dataset_path,
                    'dataset_name': dataset['name'],
                    'project_folder': dataset['project_folder']
                }
                
                # Try to get additional metadata
                try:
                    # Get the BIDSFile object for metadata
                    bids_file = layout.get_file(file_path)
                    if bids_file:
                        file_info['entities'] = bids_file.get_entities()
                        file_info['metadata'] = bids_file.get_metadata()
                except:
                    pass  # Metadata is optional
                
                all_files.append(file_info)
        
        except Exception as e:
            print(f"Error querying files in {dataset_path}: {e}")
    
    return all_files

def clear_cache():
    """Clear the BIDSLayout cache."""
    global _layout_cache
    _layout_cache.clear()
    print("BIDS layout cache cleared")

# Test function
if __name__ == '__main__':
    # Example usage
    base_dir = "/path/to/your/studies"  # Replace with actual path
    datasets = discover_bids_datasets(base_dir)
    
    for dataset in datasets:
        print(f"\nDataset: {dataset['name']}")
        print(f"Path: {dataset['path']}")
        info = get_dataset_info(dataset['path'])
        print(f"Subjects: {len(info['subjects'])}")
        print(f"Datatypes: {info['datatypes']}")
        if 'error' in info:
            print(f"Error: {info['error']}")