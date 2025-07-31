import argparse
from flask import Flask, request, render_template, jsonify
from bidsquery.config import load_base_dir, save_base_dir, choose_folder
from bidsquery.search import find_subject_files

app = Flask(__name__)

# Load or initialize the base directory
BASE_DIR = load_base_dir()
if not BASE_DIR:
    # Fallback default; you can override via --set-folder
    BASE_DIR = '/path/to/your/synology/folder'
app.config['BASE_DIR'] = BASE_DIR

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search_files():
    subject_name = request.args.get('subject')
    if not subject_name:
        return jsonify({"error": "Please provide a subject name"}), 400

    result_files = find_subject_files(subject_name, app.config['BASE_DIR'])
    return jsonify({"files": result_files})

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="BIDSQuery Flask App")
    parser.add_argument('--set-folder', action='store_true', help="Open folder chooser and save base directory")
    args = parser.parse_args()

    if args.set_folder:
        folder = choose_folder()
        if folder:
            save_base_dir(folder)
            print(f"Base directory set to: {folder}")
        else:
            print("No folder selected.")
    else:
        app.run(debug=True)