import argparse
import base64, io
from pathlib import Path
from flask import Flask, request, render_template, jsonify, redirect, url_for, flash
from config import (load_base_dir, load_participant_file_path, show_setup_dialog)
from participant_manager import load_participant_data, get_participant_summary
from query_engine import query_by_participant_name, query_by_bids_criteria, get_datasets_summary
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for plotting
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

# Global variables to store loaded data
participant_data = None
datasets_summary = None

def clear_all_caches():
    """Clear all caches to ensure clean startup."""
    global participant_data, datasets_summary
    participant_data = None
    datasets_summary = None
    
    # Clear BIDS layout cache
    try:
        from bids_manager import clear_cache
        clear_cache()
        print("Cleared BIDS layout cache")
    except Exception as e:
        print(f"Note: Could not clear BIDS cache: {e}")

def initialize_app():
    """Initialize the app with configuration and data loading."""
    global participant_data, datasets_summary
    
    # Clear all caches first for clean startup
    clear_all_caches()
    
    base_dir = load_base_dir()
    participant_file = load_participant_file_path()
    
    # Load participant data if available
    if participant_file:
        participant_data = load_participant_data(participant_file)
        if 'error' in participant_data:
            print(f"Error loading participant data: {participant_data['error']}")
            participant_data = None
    
    # Load datasets summary if base directory is available
    if base_dir:
        try:
            datasets_summary = get_datasets_summary(base_dir)
        except Exception as e:
            print(f"Error loading datasets summary: {e}")
            datasets_summary = None
    
    app.config['BASE_DIR'] = base_dir
    app.config['PARTICIPANT_FILE'] = participant_file

@app.route('/')
def index():
    """Main dashboard showing current configuration and summary info."""
    base_dir = app.config.get('BASE_DIR')
    participant_file = app.config.get('PARTICIPANT_FILE')
    # Determine if setup is complete
    setup_complete = bool(base_dir and participant_file and participant_data and datasets_summary)
    context = {
        'base_dir': base_dir,
        'participant_file': participant_file,
        'setup_complete': setup_complete,
        'participant_summary': get_participant_summary(participant_data) if participant_data else None,
        'datasets_summary': datasets_summary
    }
    return render_template('index.html', **context)

@app.route('/studies')
def studies():
    """BIDS Studies page – shows dataset descriptions, README content, and participant data summary (charts)."""
    base_dir = app.config.get('BASE_DIR')
    if not base_dir or not participant_data:
        flash('Please complete the setup first to view BIDS studies information.', 'error')
        return redirect(url_for('index'))
    # Discover datasets and attach descriptions
    datasets = []
    try:
        from bids_manager import discover_bids_datasets
        datasets = discover_bids_datasets(base_dir)
    except Exception as e:
        flash(f"Error discovering BIDS datasets: {e}", 'error')
    for ds in datasets:
        # Prepare title (Name from dataset_description or folder name)
        desc = ds.get('description', {})
        ds['title'] = desc.get('Name', ds.get('name', 'Dataset'))
        ds['bids_version'] = desc.get('BIDSVersion')
        ds['dataset_type'] = desc.get('DatasetType')
        # Read README file if present
        ds_path = Path(ds['path'])
        ds['readme'] = None
        for fname in ['README', 'README.txt', 'README.md']:
            readme_path = ds_path / fname
            if readme_path.exists():
                try:
                    ds['readme'] = readme_path.read_text(encoding='utf-8')
                except Exception as e:
                    ds['readme'] = f"[Could not read {fname}: {e}]"
                break
    # Prepare participant summary charts
    part_df = participant_data.get('data')
    total_participants = len(part_df) if part_df is not None else 0
    age_chart = None
    gender_chart = None
    if part_df is not None:
        key_cols = participant_data.get('key_columns', {})
        # Age distribution histogram
        age_col = key_cols.get('age')
        if age_col and age_col in part_df.columns:
            try:
                ages = part_df[age_col].dropna().astype(float)
            except Exception:
                ages = None
            if ages is not None and not ages.empty:
                fig, ax = plt.subplots()
                ax.hist(ages, bins=10, color='#607c8e', edgecolor='black')
                ax.set_title('Age Distribution')
                ax.set_xlabel('Age')
                ax.set_ylabel('Number of Participants')
                fig.tight_layout()
                buf = io.BytesIO()
                fig.savefig(buf, format='png')
                plt.close(fig)
                age_chart = base64.b64encode(buf.getvalue()).decode('utf-8')
        # Gender distribution bar chart
        sex_col = key_cols.get('sex')
        if sex_col and sex_col in part_df.columns:
            sexes = part_df[sex_col].dropna().astype(str).str.strip()
            if not sexes.empty:
                # Use first letter (M/F) for consistency
                counts = sexes.str[0].str.upper().value_counts()
                fig, ax = plt.subplots()
                ax.bar(counts.index, counts.values, color='#8cb369')
                ax.set_title('Gender Distribution')
                ax.set_xlabel('Sex')
                ax.set_ylabel('Number of Participants')
                fig.tight_layout()
                buf = io.BytesIO()
                fig.savefig(buf, format='png')
                plt.close(fig)
                gender_chart = base64.b64encode(buf.getvalue()).decode('utf-8')
    context = {
        'datasets': datasets,
        'participant_count': total_participants,
        'age_chart': age_chart,
        'gender_chart': gender_chart
    }
    return render_template('studies.html', **context)

@app.route('/setup-gui')
def setup_gui():
    """Launch GUI setup dialog for selecting base directory and participant file."""
    show_setup_dialog()
    initialize_app()  # Reload configuration after user input
    flash('Configuration updated via GUI dialog!', 'success')
    return redirect(url_for('index'))

@app.route('/search-by-name', methods=['GET', 'POST'])
def search_by_name():
    """Search for BIDS files by participant name."""
    if request.method == 'GET':
        return render_template('search_by_name.html')
    # Handle search submission
    name_query = request.json.get('name') if request.is_json else request.form.get('name')
    if not name_query or not name_query.strip():
        return jsonify({"error": "Please provide a name to search for"}), 400
    if not participant_data:
        return jsonify({"error": "Participant data not loaded. Please complete setup first."}), 400
    if not app.config.get('BASE_DIR'):
        return jsonify({"error": "Base directory not configured. Please complete setup first."}), 400
    try:
        results = query_by_participant_name(name_query.strip(), app.config['BASE_DIR'], participant_data)
        return jsonify(results) if request.is_json else render_template('search_results.html', results=results)
    except Exception as e:
        error_msg = f"Search error: {e}"
        if request.is_json:
            return jsonify({"error": error_msg}), 500
        flash(error_msg, 'error')
        return render_template('search_by_name.html')

@app.route('/search-by-criteria', methods=['GET', 'POST'])
def search_by_criteria():
    """Search for participants by BIDS and demographic criteria."""
    if request.method == 'GET':
        return render_template('search_by_criteria.html')
    # Handle search submission
    criteria = request.json if request.is_json else {k: v.strip() for k, v in request.form.items() if v.strip()}
    if not criteria:
        return jsonify({"error": "Please provide search criteria"}), 400
    if not participant_data:
        return jsonify({"error": "Participant data not loaded. Please complete setup first."}), 400
    if not app.config.get('BASE_DIR'):
        return jsonify({"error": "Base directory not configured. Please complete setup first."}), 400
    try:
        results = query_by_bids_criteria(app.config['BASE_DIR'], participant_data, **criteria)
        return jsonify(results) if request.is_json else render_template('search_results.html', results=results)
    except Exception as e:
        error_msg = f"Search error: {e}"
        print(f"Detailed error in search_by_criteria: {e}")  # Debug logging
        import traceback
        traceback.print_exc()  # Print full traceback for debugging
        if request.is_json:
            return jsonify({"error": error_msg}), 500
        flash(error_msg, 'error')
        return render_template('search_by_criteria.html')

@app.route('/api/datasets')
def api_datasets():
    """API endpoint to get datasets summary."""
    if not datasets_summary:
        return jsonify({"error": "No datasets loaded"}), 400
    return jsonify(datasets_summary)

@app.route('/api/participant-summary')
def api_participant_summary():
    """API endpoint to get participant data summary."""
    if not participant_data:
        return jsonify({"error": "No participant data loaded"}), 400
    summary = get_participant_summary(participant_data)
    summary.pop('sample_data', None)  # omit sample data for brevity
    return jsonify(summary)

@app.route('/reload-data')
def reload_data():
    """Reload all data from disk (datasets and participant info)."""
    try:
        initialize_app()
        flash('Data reloaded successfully!', 'success')
    except Exception as e:
        flash(f'Error reloading data: {e}', 'error')
    return redirect(url_for('index'))

# Error handlers for user feedback
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error_code=404, error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error_code=500, error_message="Internal server error"), 500

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="BIDSQuery Flask App")
    parser.add_argument('--setup', action='store_true', help="Open GUI setup dialog and save configuration")
    parser.add_argument('--port', type=int, default=5000, help="Port to run the Flask app on (default: 5000)")
    parser.add_argument('--debug', action='store_true', help="Run Flask app in debug mode")
    args = parser.parse_args()
    
    if args.setup:
        show_setup_dialog()
        print("Setup completed. You can now run the app without the --setup flag.")
    else:
        initialize_app()
        # If not configured, remind user to run setup
        if not app.config.get('BASE_DIR') or not app.config.get('PARTICIPANT_FILE'):
            print("\n" + "="*60)
            print("SETUP REQUIRED")
            print("="*60)
            print("Before using the app, please configure the application:")
            print(" - Run with --setup flag to launch the GUI setup dialog:")
            print(f"   python {__file__} --setup")
            print("="*60 + "\n")
        
        print(f"Starting BIDSQuery app on http://localhost:{args.port}")
        print("Press Ctrl+C to stop the server")
        # Changed: Only bind to localhost (127.0.0.1) instead of all interfaces (0.0.0.0)
        app.run(debug=args.debug, port=args.port, host='127.0.0.1')