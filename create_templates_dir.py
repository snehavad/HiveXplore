# This file will be replaced by v:\Code\ProjectCode\HiveBuzz\utils\setup.py
# Keeping content for reference
import os
import shutil

# Create templates directory if it doesn't exist
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
os.makedirs(templates_dir, exist_ok=True)

print(f"Created templates directory at {templates_dir}")
