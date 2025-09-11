# Complete BIDSQuery Implementation Guide

## Overview

BIDSQuery is a Flask web application that bridges the gap between sensitive participant information and anonymized BIDS neuroimaging datasets. It allows researchers to:

1. **Search by participant name** → Find their BIDS files
2. **Search by BIDS criteria** (T1w, age>60, etc.) → Find matching participants
3. **Maintain security** while linking sensitive and anonymous data

## Build
```python
pyinstaller --onefile --name BIDSQuery --add-data "templates;templates" app.py
```

## Directory Structure

```
bidsquery/
├── app.py                     # Main Flask application
├── config.py                  # Configuration management
├── bids_manager.py            # BIDS dataset discovery and management
├── participant_manager.py     # Participant data handling
├── query_engine.py            # Query processing and filtering
├── requirements.txt           # Python dependencies
├── templates/
│   ├── index.html             # Main dashboard
│   ├── search_by_name.html    # Name search interface
│   ├── search_by_criteria.html # Criteria search interface
│   ├── search_results.html    # Results display
│   └── setup.html             # Configuration setup
└── README.md                  # Documentation
```

## Core Components Explained

### 1. **app.py** - Main Application
- **Purpose**: Flask web server and routing
- **Key Features**:
  - Web interface for all functionality
  - Configuration management
  - Search endpoints
  - Result display
  - Security-focused design

### 2. **config.py** - Configuration Management
- **Purpose**: Handle all configuration settings
- **Key Functions**:
  - `show_setup_dialog()`: GUI setup interface
  - `load_base_dir()` / `save_base_dir()`: Directory management
  - `load_participant_file_path()` / `save_participant_file_path()`: Participant file management
- **Storage**: Uses JSON config file in user's home directory

### 3. **bids_manager.py** - BIDS Dataset Management
- **Purpose**: Discover and manage BIDS datasets
- **Key Functions**:
  - `discover_bids_datasets()`: Find all BIDS datasets in directory tree
  - `get_bids_layout()`: Create/cache BIDSLayout objects
  - `find_subject_files_all_datasets()`: Find files for specific subject
  - `query_bids_files()`: Query files by BIDS criteria
- **Performance**: Uses caching to avoid recreating BIDSLayout objects

### 4. **participant_manager.py** - Participant Data Management
- **Purpose**: Handle sensitive participant information
- **Key Functions**:
  - `load_participant_data()`: Load CSV/Excel participant files
  - `find_participant_by_name()`: Search by name (partial matching)
  - `find_participant_by_id()`: Look up by participant ID
  - `filter_participants_by_criteria()`: Apply demographic filters
- **Smart Detection**: Automatically identifies key columns (name, ID, age, etc.)

### 5. **query_engine.py** - Query Processing
- **Purpose**: Connect BIDS data with participant information
- **Key Functions**:
  - `query_by_participant_name()`: Name → BIDS files
  - `query_by_bids_criteria()`: BIDS criteria → participants
  - `get_datasets_summary()`: Overview of available data

## How to Test Without Building

**You should NOT build the app yet!** Test it first as a regular Python application:

### Step 1: Set Up Environment
```bash
# Create virtual environment
python -m venv bidsquery_env

# Activate it (Windows)
bidsquery_env\Scripts\activate
# Or on Mac/Linux
source bidsquery_env/bin/activate

# Install dependencies
pip install flask pandas pybids openpyxl
```

### Step 2: Create Test Data Structure
```
test_data/
├── study1/
│   └── bids/
│       ├── dataset_description.json
│       ├── sub-001/
│       │   └── anat/
│       │       └── sub-001_T1w.nii.gz
│       └── sub-002/
│           └── anat/
│               └── sub-002_T1w.nii.gz
├── study2/
│   └── bids/
│       └── dataset_description.json
└── participants.csv
```

### Step 3: Create Test Files

**participants.csv:**
```csv
participant_id,name,age,sex,diagnosis
sub-001,John Doe,65,M,control
sub-002,Jane Smith,70,F,patient
```

**dataset_description.json:**
```json
{
    "Name": "Test Dataset",
    "BIDSVersion": "1.8.0",
    "DatasetType": "raw"
}
```

### Step 4: Test Individual Components
```python
# Test config.py
from config import load_base_dir, show_setup_dialog
print(load_base_dir())  # Should return None first time

# Test participant_manager.py
from participant_manager import load_participant_data
data = load_participant_data("test_data/participants.csv")
print(data)

# Test bids_manager.py
from bids_manager import discover_bids_datasets
datasets = discover_bids_datasets("test_data")
print(datasets)
```

### Step 5: Run the Flask App
```bash
python app.py --setup  # First, configure directories
python app.py          # Then run the app
```

Visit `http://localhost:5000` in your browser.

## Testing Strategy

### Phase 1: Component Testing
1. **Test each module individually** with simple print statements
2. **Verify file loading** works with your test data
3. **Check BIDS discovery** finds your test datasets

### Phase 2: Integration Testing
1. **Run Flask app** in development mode
2. **Test web interface** with your test data
3. **Verify both search directions** work

### Phase 3: Real Data Testing
1. **Use actual BIDS datasets** (small ones first)
2. **Test with real participant files**
3. **Verify performance** with larger datasets

## Common Issues & Solutions

### Issue 1: BIDS Layout Creation Fails
**Problem**: `BIDSLayout()` throws errors
**Solution**: Ensure your BIDS dataset has proper `dataset_description.json`

### Issue 2: Participant File Not Loading
**Problem**: CSV/Excel files not recognized
**Solution**: Check file format, ensure proper column headers

### Issue 3: No Datasets Found
**Problem**: `discover_bids_datasets()` returns empty list
**Solution**: Verify folder structure has `dataset_description.json` in BIDS folders

## VSCode JavaScript Issue Fix

The VSCode error is because Jinja2 templates inside JavaScript confuse the parser.

# Complete BIDSQuery Implementation Guide

## Overview

BIDSQuery is a Flask web application that bridges the gap between sensitive participant information and anonymized BIDS neuroimaging datasets. It allows researchers to:

1. **Search by participant name** → Find their BIDS files
2. **Search by BIDS criteria** (T1w, age>60, etc.) → Find matching participants
3. **Maintain security** while linking sensitive and anonymous data

## Directory Structure

```
bidsquery/
├── app.py                     # Main Flask application
├── config.py                  # Configuration management
├── bids_manager.py            # BIDS dataset discovery and management
├── participant_manager.py     # Participant data handling
├── query_engine.py            # Query processing and filtering
├── requirements.txt           # Python dependencies
├── templates/
│   ├── index.html             # Main dashboard
│   ├── search_by_name.html    # Name search interface
│   ├── search_by_criteria.html # Criteria search interface
│   ├── search_results.html    # Results display
│   └── setup.html             # Configuration setup
└── README.md                  # Documentation
```

## Core Components Explained

### 1. **app.py** - Main Application
- **Purpose**: Flask web server and routing
- **Key Features**:
  - Web interface for all functionality
  - Configuration management
  - Search endpoints
  - Result display
  - Security-focused design

### 2. **config.py** - Configuration Management
- **Purpose**: Handle all configuration settings
- **Key Functions**:
  - `show_setup_dialog()`: GUI setup interface
  - `load_base_dir()` / `save_base_dir()`: Directory management
  - `load_participant_file_path()` / `save_participant_file_path()`: Participant file management
- **Storage**: Uses JSON config file in user's home directory

### 3. **bids_manager.py** - BIDS Dataset Management
- **Purpose**: Discover and manage BIDS datasets
- **Key Functions**:
  - `discover_bids_datasets()`: Find all BIDS datasets in directory tree
  - `get_bids_layout()`: Create/cache BIDSLayout objects
  - `find_subject_files_all_datasets()`: Find files for specific subject
  - `query_bids_files()`: Query files by BIDS criteria
- **Performance**: Uses caching to avoid recreating BIDSLayout objects

### 4. **participant_manager.py** - Participant Data Management
- **Purpose**: Handle sensitive participant information
- **Key Functions**:
  - `load_participant_data()`: Load CSV/Excel participant files
  - `find_participant_by_name()`: Search by name (partial matching)
  - `find_participant_by_id()`: Look up by participant ID
  - `filter_participants_by_criteria()`: Apply demographic filters
- **Smart Detection**: Automatically identifies key columns (name, ID, age, etc.)

### 5. **query_engine.py** - Query Processing
- **Purpose**: Connect BIDS data with participant information