"""
CSS Build Script for HiveBuzz

This script combines CSS files from different directories into single files
for better performance in production.

Usage:
    python build_css.py
"""

import glob
import os
import re

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSS_DIR = os.path.join(BASE_DIR, "static", "css")
COMPONENTS_DIR = os.path.join(CSS_DIR, "components")
PAGES_DIR = os.path.join(CSS_DIR, "pages")
OUTPUT_DIR = os.path.join(CSS_DIR, "dist")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)


def read_file(filepath):
    """Read a file and return its contents as string"""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def write_file(filepath, content):
    """Write content to a file"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Created: {filepath}")


def process_imports(content, base_dir):
    """Process @import statements recursively"""
    import_re = re.compile(r'@import\s+[\'"]([^\'"]+)[\'"];')

    def replace_import(match):
        import_path = match.group(1)
        if import_path.startswith("http"):
            # Keep external imports
            return match.group(0)

        # Resolve path relative to the base directory
        full_path = os.path.join(base_dir, import_path)
        if not os.path.exists(full_path):
            print(f"Warning: Import not found: {full_path}")
            return f"/* Import not found: {import_path} */"

        imported_content = read_file(full_path)
        # Process nested imports
        imported_content = process_imports(imported_content, os.path.dirname(full_path))
        return f"/* {import_path} */\n{imported_content}\n"

    return import_re.sub(replace_import, content)


def build_main_css():
    """Build the main CSS file"""
    print("Building main.css...")

    # Start with the base style file
    main_content = read_file(os.path.join(CSS_DIR, "style.css"))

    # Process and replace @import statements
    processed_content = process_imports(main_content, CSS_DIR)

    # Add component styles
    for component_file in glob.glob(os.path.join(COMPONENTS_DIR, "*.css")):
        component_name = os.path.basename(component_file)
        component_content = read_file(component_file)
        processed_content += (
            f"\n/* Component: {component_name} */\n{component_content}\n"
        )

    # Write the final file
    write_file(os.path.join(OUTPUT_DIR, "main.css"), processed_content)


def build_page_css_files():
    """Build separate CSS files for each page"""
    print("Building page-specific CSS files...")

    for page_file in glob.glob(os.path.join(PAGES_DIR, "*.css")):
        page_name = os.path.basename(page_file)
        print(f"Processing {page_name}...")

        # Read page CSS
        page_content = read_file(page_file)

        # Process imports
        processed_content = process_imports(page_content, PAGES_DIR)

        # Write the page CSS
        write_file(os.path.join(OUTPUT_DIR, page_name), processed_content)


if __name__ == "__main__":
    build_main_css()
    build_page_css_files()
    print("CSS build completed!")
