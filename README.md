# Complete BIDSQuery Implementation Guide

## Overview

BIDSQuery is a Flask web application that bridges the gap between sensitive participant information and anonymized BIDS neuroimaging datasets. It allows researchers to:

1. **Search by participant name** → Find their BIDS files
2. **Search by BIDS criteria** (T1w, age>60, etc.) → Find matching participants
3. **Maintain security** while linking sensitive and anonymous data

## Build

Build is done with `pyinstaller`. It requires a `.spec` for the build.

```python
# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

project_root = Path(os.getcwd())

# --- Data files ---
datas = []
# PyBIDS configs (e.g., bids/layout/config/*.json)
datas += collect_data_files('bids')
# BIDS schema (critical): bidsschematools/data/schema/*
datas += collect_data_files('bidsschematools')

# Flask templates/static
tpl = project_root / 'templates'
sta = project_root / 'static'
if tpl.exists():
    datas.append((str(tpl), 'templates'))
if sta.exists():
    datas.append((str(sta), 'static'))

# --- Hidden imports (keep minimal but safe) ---
hiddenimports = []
hiddenimports += collect_submodules('bids')               # pybids internals
hiddenimports += collect_submodules('bidsschematools')    # schema loaders
hiddenimports += [
    'tkinter',                              # GUI setup dialog
    'matplotlib.backends.backend_agg',      # headless plotting
    'jinja2.ext',
]

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Slim it down: exclude stuff you don't use
    excludes=[
        'sklearn', 'scipy',
        'numpy.tests', 'pandas.tests', 'matplotlib.tests',
        'IPython', 'jupyter', 'PyQt5', 'PySide6'
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# onedir build for debuggability; size similar to onefile but easier to inspect
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BIDSQuery',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,     # keep console so you can see stack traces
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BIDSQuery'
)
```

Build in virtual environment for light .exe file.

```shell
py -3.12 -m venv venv
venv\Scripts\pip install flask pandas pybids matplotlib openpyxl
venv\Scripts\pip install pyinstaller
venv\Scripts\pyinstaller --clean BIDSQuery.spec
```


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

