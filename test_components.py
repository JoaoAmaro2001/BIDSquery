#!/usr/bin/env python3
"""
Test script for BIDSQuery components
Run this to verify each component works before testing the full app.
"""

import os
import sys
import json
import pandas as pd
from pathlib import Path

def create_test_data():
    """Create minimal test data structure for testing."""
    print("Creating test data structure...")
    
    # Create directory structure
    test_dir = Path("test_data")
    test_dir.mkdir(exist_ok=True)
    
    # Study 1
    study1 = test_dir / "study1" / "bids"
    study1.mkdir(parents=True, exist_ok=True)
    
    # Create dataset_description.json for study1
    dataset_desc1 = {
        "Name": "Test Study 1",
        "BIDSVersion": "1.8.0",
        "DatasetType": "raw",
        "Authors": ["Test Author"]
    }
    
    with open(study1 / "dataset_description.json", 'w') as f:
        json.dump(dataset_desc1, f, indent=2)
    
    # Create subject folders
    (study1 / "sub-001" / "anat").mkdir(parents=True, exist_ok=True)
    (study1 / "sub-002" / "anat").mkdir(parents=True, exist_ok=True)
    
    # Create dummy files (empty for testing)
    (study1 / "sub-001" / "anat" / "sub-001_T1w.nii.gz").touch()
    (study1 / "sub-002" / "anat" / "sub-002_T1w.nii.gz").touch()
    
    # Study 2
    study2 = test_dir / "study2" / "bids"
    study2.mkdir(parents=True, exist_ok=True)
    
    dataset_desc2 = {
        "Name": "Test Study 2", 
        "BIDSVersion": "1.8.0",
        "DatasetType": "raw"
    }
    
    with open(study2 / "dataset_description.json", 'w') as f:
        json.dump(dataset_desc2, f, indent=2)
    
    (study2 / "sub-003" / "func").mkdir(parents=True, exist_ok=True)
    (study2 / "sub-003" / "func" / "sub-003_task-rest_bold.nii.gz").touch()
    
    # Create participants.csv
    participants_data = {
        'participant_id': ['sub-001', 'sub-002', 'sub-003'],
        'name': ['John Doe', 'Jane Smith', 'Bob Johnson'],
        'age': [65, 70, 45],
        'sex': ['M', 'F', 'M'],
        'diagnosis': ['control', 'patient', 'control']
    }
    
    df = pd.DataFrame(participants_data)
    df.to_csv(test_dir / "participants.csv", index=False)
    
    print(f"✅ Test data created in: {test_dir.absolute()}")
    return test_dir

def test_config():
    """Test configuration management."""
    print("\n" + "="*50)
    print("TESTING CONFIG.PY")
    print("="*50)
    
    try:
        from config import load_base_dir, save_base_dir, load_participant_file_path
        
        print("Testing config loading...")
        base_dir = load_base_dir()
        participant_file = load_participant_file_path()
        
        print(f"Current base directory: {base_dir}")
        print(f"Current participant file: {participant_file}")
        
        print("✅ Config module loaded successfully")
        return True
        
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def test_participant_manager(test_data_dir):
    """Test participant data management."""
    print("\n" + "="*50)
    print("TESTING PARTICIPANT_MANAGER.PY")
    print("="*50)
    
    try:
        from participant_manager import (load_participant_data, find_participant_by_name, 
                                       get_participant_summary, find_participant_by_id)
        
        # Test loading participant data
        participant_file = test_data_dir / "participants.csv"
        print(f"Loading participant data from: {participant_file}")
        
        participant_data = load_participant_data(str(participant_file))
        
        if 'error' in participant_data:
            print(f"❌ Error loading participant data: {participant_data['error']}")
            return False
        
        print(f"✅ Loaded {participant_data['row_count']} participants")
        print(f"Columns: {participant_data['columns']}")
        print(f"Key columns identified: {participant_data['key_columns']}")
        
        # Test search by name
        print("\nTesting name search...")
        matches = find_participant_by_name(participant_data, "john")
        print(f"Found {len(matches)} matches for 'john': {matches}")
        
        # Test search by ID
        print("\nTesting ID search...")
        participant = find_participant_by_id(participant_data, "sub-001")
        print(f"Found participant for sub-001: {participant}")
        
        print("✅ Participant manager tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Participant manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_bids_manager(test_data_dir):
    """Test BIDS dataset management."""
    print("\n" + "="*50)
    print("TESTING BIDS_MANAGER.PY")
    print("="*50)
    
    try:
        from bids_manager import (discover_bids_datasets, get_dataset_info, 
                                find_subject_files_all_datasets)
        
        print(f"Discovering BIDS datasets in: {test_data_dir}")
        datasets = discover_bids_datasets(str(test_data_dir))
        
        print(f"✅ Found {len(datasets)} BIDS datasets:")
        for i, dataset in enumerate(datasets):
            print(f"  {i+1}. {dataset['name']} - {dataset['path']}")
            
            # Test getting dataset info
            info = get_dataset_info(dataset['path'])
            print(f"     Subjects: {info['subjects']}")
            print(f"     Data types: {info['datatypes']}")
        
        if datasets:
            # Test finding files for a subject
            print("\nTesting subject file search...")
            files = find_subject_files_all_datasets("001", datasets)
            print(f"Found {len(files)} files for subject 001:")
            for file_info in files[:3]:  # Show first 3
                print(f"  - {file_info['path']}")
        
        print("✅ BIDS manager tests passed")
        return True
        
    except Exception as e:
        print(f"❌ BIDS manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_query_engine(test_data_dir):
    """Test query engine."""
    print("\n" + "="*50)
    print("TESTING QUERY_ENGINE.PY")
    print("="*50)
    
    try:
        from query_engine import query_by_participant_name, query_by_bids_criteria, get_datasets_summary
        from participant_manager import load_participant_data
        
        # Load test data
        participant_file = test_data_dir / "participants.csv"
        participant_data = load_participant_data(str(participant_file))
        
        if 'error' in participant_data:
            print(f"❌ Cannot load participant data: {participant_data['error']}")
            return False
        
        # Test datasets summary
        print("Testing datasets summary...")
        summary = get_datasets_summary(str(test_data_dir))
        print(f"Datasets summary: {summary['total_datasets']} datasets")
        
        # Test query by name
        print("\nTesting query by participant name...")
        results = query_by_participant_name("john", str(test_data_dir), participant_data)
        print(f"Query by name results: {len(results['participants_found'])} participants, {results['total_files']} files")
        
        # Test query by criteria
        print("\nTesting query by criteria...")
        results2 = query_by_bids_criteria(str(test_data_dir), participant_data, datatype='anat')
        print(f"Query by criteria results: {len(results2['participants_found'])} participants, {results2['total_files']} files")
        
        print("✅ Query engine tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Query engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all component tests."""
    print("🧪 BIDSQuery Component Testing")
    print("="*60)
    
    # Create test data
    test_data_dir = create_test_data()
    
    # Run tests
    tests = [
        ("Config", test_config),
        ("Participant Manager", lambda: test_participant_manager(test_data_dir)),
        ("BIDS Manager", lambda: test_bids_manager(test_data_dir)),
        ("Query Engine", lambda: test_query_engine(test_data_dir))
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            if callable(test_func):
                results[test_name] = test_func()
            else:
                results[test_name] = test_func
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = 0
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:.<30} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! You can now test the Flask app:")
        print("   python app.py --setup    # Configure directories")
        print("   python app.py            # Run the web app")
    else:
        print(f"\n⚠️  {len(results)-passed} tests failed. Fix these issues before running the app.")
    
    print(f"\nTest data location: {test_data_dir.absolute()}")

if __name__ == "__main__":
    main()