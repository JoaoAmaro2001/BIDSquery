# BIDSQuery

A lightweight Flask app to search BIDS datasets for a given subject name.

## Installation

```bash
pip install -r requirements.txt
```

## Build

Build app with:
```bash
pyinstaller --onefile --name BIDSQuery --add-data "templates;templates" app.py
```