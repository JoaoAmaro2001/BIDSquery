import os
from bids.layout import BIDSLayout


def find_subject_files(subject, base_dir):
    """Search all BIDS datasets under base_dir for files matching the given subject."""
    result_files = []
    for root, dirs, files in os.walk(base_dir):
        if 'dataset_description.json' in files:
            layout = BIDSLayout(root)
            # Return file paths directly
            found = layout.get(subject=subject, return_type='filename')
            result_files.extend(found)
    return result_files