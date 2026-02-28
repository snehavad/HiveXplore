# This file will be replaced by v:\Code\ProjectCode\HiveBuzz\utils\setup.py
# Keeping content for reference
import os

# Define base directory
base_dir = os.path.dirname(__file__)

# Create static directory and subdirectories
static_dir = os.path.join(base_dir, "static")
static_dirs = ["css", "js", "img", "css/components", "css/pages", "img/illustrations"]

for subdir in static_dirs:
    dir_path = os.path.join(static_dir, subdir)
    os.makedirs(dir_path, exist_ok=True)
    print(f"Created directory: {dir_path}")

# Create an empty CSS file if it doesn't exist
style_css_path = os.path.join(static_dir, "css", "style.css")
if not os.path.exists(style_css_path):
    with open(style_css_path, "w") as f:
        f.write("/* Main HiveBuzz stylesheet */\n")
    print(f"Created empty style.css file at {style_css_path}")

print("Static directory structure created successfully!")
