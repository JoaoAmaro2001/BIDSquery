import os
import json
import time
from pathlib import Path
from bids.layout import BIDSLayout
from config import load_cache, save_cache

# Global cache to store BIDSLayout objects (process-memory)
_layout_cache = {}

def _is_valid_bids_dir(p: Path) -> bool:
    """Quick validation: folder exists and has dataset_description.json."""
    return p.exists() and (p / "dataset_description.json").exists()

def _load_cached_datasets(base_dir: Path, cache_ttl_hours=None):
    """
    Return cached datasets for base_dir if still valid.
    Validates existence of each 'bids' path and optional TTL.
    """
    cache = load_cache() or {}
    entry = cache.get(str(base_dir))
    if not entry:
        return None

    # TTL check (optional)
    if cache_ttl_hours is not None:
        ts = entry.get("timestamp", 0)
        age_hours = (time.time() - ts) / 3600.0
        if age_hours > cache_ttl_hours:
            return None

    datasets = entry.get("datasets") or []
    # Validate each cached path
    valid = []
    for d in datasets:
        p = Path(d["path"])
        if _is_valid_bids_dir(p):
            valid.append(d)

    # If any invalidated, force rescan
    if len(valid) != len(datasets):
        return None
    return valid

def _save_cached_datasets(base_dir: Path, datasets: list):
    cache = load_cache() or {}
    cache[str(base_dir)] = {
        "timestamp": time.time(),
        "datasets": datasets,
    }
    save_cache(cache)

def discover_bids_datasets(base_dir, max_levels=3, use_cache=True, refresh=False, cache_ttl_hours=None):
    """
    Discover BIDS datasets by locating directories named 'bids' (case-insensitive),
    searching only up to `max_levels` directory levels below `base_dir` for speed.

    With caching:
      - If use_cache and not refresh, try the persisted cache first.
      - Validate cached paths; if invalid/stale, fall back to filesystem scan and update cache.
    """
    base_path = Path(base_dir).resolve()
    datasets = []

    if not base_path.exists():
        print(f"Warning: Base directory does not exist: {base_path}")
        return datasets

    # 0) Try persisted cache first
    if use_cache and not refresh:
        cached = _load_cached_datasets(base_path, cache_ttl_hours=cache_ttl_hours)
        if cached is not None:
            print(f"Using cached BIDS studies for: {base_path}  (n={len(cached)})")
            return cached

    print(f"Scanning for 'bids' folders (depth ≤ {max_levels}) in: {base_path}")

    # 1) Collect ALL directories named 'bids' within the depth limit
    bids_dirs = []
    for root, dirs, _files in os.walk(base_path, topdown=True):
        rel = Path(root).resolve().relative_to(base_path)
        depth = len(rel.parts)
        if depth >= max_levels:
            dirs[:] = []
            continue
        for d in dirs:
            if d.lower() == "bids":
                bids_dirs.append((Path(root) / d).resolve())

    if not bids_dirs:
        print("No 'bids' folders found within the depth limit.")
        # Also write empty to cache so we don't keep re-scanning if user wants that behavior
        if use_cache:
            _save_cached_datasets(base_path, [])
        return datasets

    # 2) Sort by path depth (shallower first), then lexicographically
    bids_dirs = sorted(bids_dirs, key=lambda p: (len(p.parts), str(p)))

    # 3) Keep only the first (most-upstream) 'bids' per study (study = parent of 'bids')
    selected_study_roots = []
    for bids_dir in bids_dirs:
        study_dir = bids_dir.parent
        skip = any(bids_dir.is_relative_to(study_root) for study_root in selected_study_roots)
        if skip:
            continue

        selected_study_roots.append(study_dir)

        dataset_info = {
            "path": str(bids_dir),
            "name": study_dir.name,
            "project_folder": str(study_dir.parent),
            "description": {},
        }

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

    # 4) Persist results to cache
    if use_cache:
        _save_cached_datasets(base_path, datasets)

    return datasets

def clear_cache():
    """Clear the in-process BIDSLayout cache only."""
    global _layout_cache
    _layout_cache.clear()
    print("BIDS layout cache cleared")

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