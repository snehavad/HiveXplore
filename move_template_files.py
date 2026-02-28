# This file will be replaced by v:\Code\ProjectCode\HiveBuzz\utils\setup.py
# Keeping content for reference
import os
import shutil

# Define source and destination paths
base_dir = os.path.dirname(__file__)
templates_dir = os.path.join(base_dir, "templates")

# Ensure templates directory exists
os.makedirs(templates_dir, exist_ok=True)

# Template files to move from root to templates directory
template_files = ["landing.html", "toggle_switch.html"]

for file in template_files:
    source_path = os.path.join(base_dir, file)
    dest_path = os.path.join(templates_dir, file)

    if os.path.exists(source_path):
        # Copy the file to the templates directory
        shutil.copy2(source_path, dest_path)
        print(f"Copied {file} to templates directory")
    else:
        print(f"Warning: {file} not found in root directory")

print("Template files moved successfully!")
