import argparse
from flask import Flask, request, render_template, jsonify, redirect, url_for, flash
from config import (load_base_dir, load_participant_file_path, show_setup_dialog, 
                   save_base_dir, save_participant_file_path, choose_folder, choose_participant_file)
from participant_manager import load_participant_data, get_participant_summary
from query_engine import query_by_participant_name, query_by_bids_criteria, get_datasets_summary

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

# Global variables to store loaded data
participant_data = None
datasets_summary = None

def initialize_app():
    """Initialize the app with configuration and data loading."""
    global participant_data, datasets_summary
    
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
    """Main page showing current configuration and available actions."""
    base_dir = app.config.get('BASE_DIR')
    participant_file = app.config.get('PARTICIPANT_FILE')
    
    # Check if setup is complete
    setup_complete = base_dir and participant_file and participant_data and datasets_summary
    
    context = {
        'base_dir': base_dir,
        'participant_file': participant_file,
        'setup_complete': setup_complete,
        'participant_summary': get_participant_summary(participant_data) if participant_data else None,
        'datasets_summary': datasets_summary
    }
    
    return render_template('index.html', **context)

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    """Configuration setup page."""
    if request.method == 'POST':
        # Handle form submission
        base_dir = request.form.get('base_dir')
        participant_file = request.form.get('participant_file')
        
        if base_dir:
            save_base_dir(base_dir)
        if participant_file:
            save_participant_file_path(participant_file)
        
        # Reinitialize the app with new configuration
        initialize_app()
        
        flash('Configuration updated successfully!', 'success')
        return redirect(url_for('index'))
    
    # Show current configuration
    context = {
        'base_dir': app.config.get('BASE_DIR', ''),
        'participant_file': app.config.get('PARTICIPANT_FILE', '')
    }
    
    return render_template('setup.html', **context)

@app.route('/setup-gui')
def setup_gui():
    """Launch GUI setup dialog."""
    show_setup_dialog()
    initialize_app()  # Reload configuration
    flash('Configuration updated via GUI dialog!', 'success')
    return redirect(url_for('index'))

@app.route('/search-by-name', methods=['GET', 'POST'])
def search_by_name():
    """Search for BIDS files by participant name."""
    if request.method == 'GET':
        return render_template('search_by_name.html')
    
    # POST request - perform search
    # Fix: Properly handle both JSON and form data
    if request.is_json:
        name_query = request.json.get('name')
    else:
        name_query = request.form.get('name')
    
    if not name_query or not name_query.strip():
        return jsonify({"error": "Please provide a name to search for"}), 400
    
    if not participant_data:
        return jsonify({"error": "Participant data not loaded. Please complete setup first."}), 400
    
    if not app.config['BASE_DIR']:
        return jsonify({"error": "Base directory not configured. Please complete setup first."}), 400
    
    try:
        results = query_by_participant_name(name_query.strip(), app.config['BASE_DIR'], participant_data)
        
        if request.is_json:
            return jsonify(results)
        else:
            return render_template('search_results.html', results=results)
            
    except Exception as e:
        error_msg = f"Search error: {str(e)}"
        if request.is_json:
            return jsonify({"error": error_msg}), 500
        else:
            flash(error_msg, 'error')
            return render_template('search_by_name.html')

@app.route('/search-by-criteria', methods=['GET', 'POST'])
def search_by_criteria():
    """Search for participants by BIDS and demographic criteria."""
    if request.method == 'GET':
        return render_template('search_by_criteria.html')
    
    # POST request - perform search
    # Fix: Properly handle both JSON and form data
    if request.is_json:
        criteria = request.json
    else:
        criteria = {}
        # Extract criteria from form
        for key, value in request.form.items():
            if value.strip():  # Only include non-empty values
                criteria[key] = value.strip()
    
    if not criteria:
        return jsonify({"error": "Please provide search criteria"}), 400
    
    if not participant_data:
        return jsonify({"error": "Participant data not loaded. Please complete setup first."}), 400
    
    if not app.config['BASE_DIR']:
        return jsonify({"error": "Base directory not configured. Please complete setup first."}), 400
    
    try:
        results = query_by_bids_criteria(app.config['BASE_DIR'], participant_data, **criteria)
        
        if request.is_json:
            return jsonify(results)
        else:
            return render_template('search_results.html', results=results)
            
    except Exception as e:
        error_msg = f"Search error: {str(e)}"
        if request.is_json:
            return jsonify({"error": error_msg}), 500
        else:
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
    # Remove sensitive sample data for API response
    if 'sample_data' in summary:
        del summary['sample_data']
    
    return jsonify(summary)

@app.route('/reload-data')
def reload_data():
    """Reload all data (datasets and participant info)."""
    try:
        initialize_app()
        flash('Data reloaded successfully!', 'success')
    except Exception as e:
        flash(f'Error reloading data: {str(e)}', 'error')
    
    return redirect(url_for('index'))

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', 
                         error_code=404, 
                         error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', 
                         error_code=500, 
                         error_message="Internal server error"), 500

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="BIDSQuery Flask App")
    parser.add_argument('--setup', action='store_true', 
                       help="Open GUI setup dialog and save configuration")
    parser.add_argument('--port', type=int, default=5000,
                       help="Port to run the Flask app on (default: 5000)")
    parser.add_argument('--debug', action='store_true',
                       help="Run Flask app in debug mode")
    args = parser.parse_args()

    if args.setup:
        show_setup_dialog()
        print("Setup completed. You can now run the app without --setup flag.")
    else:
        # Initialize the app
        initialize_app()
        
        # Check if basic setup is complete
        if not app.config['BASE_DIR'] or not app.config['PARTICIPANT_FILE']:
            print("\n" + "="*60)
            print("SETUP REQUIRED")
            print("="*60)
            print("Before using the app, please complete the setup:")
            print("1. Run with --setup flag to use GUI setup dialog:")
            print(f"   python {__file__} --setup")
            print("2. Or visit http://localhost:{}/setup after starting the app")
            print("="*60 + "\n")
        
        # Start the Flask app
        print(f"Starting BIDSQuery app on http://localhost:{args.port}")
        print("Press Ctrl+C to stop the server")
        
        app.run(debug=args.debug, port=args.port, host='0.0.0.0')