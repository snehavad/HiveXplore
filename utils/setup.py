"""
HiveBuzz Setup Utility
Handles project initialization, directory creation, and file management
"""

import os
import shutil
import sys


class HiveBuzzSetup:
    """
    Setup utility for HiveBuzz application
    """

    def __init__(self, base_dir=None):
        """Initialize with the project base directory"""
        if base_dir is None:
            # Default to the parent of the directory containing this script
            self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        else:
            self.base_dir = base_dir

        self.templates_dir = os.path.join(self.base_dir, "templates")
        self.static_dir = os.path.join(self.base_dir, "static")
        self.utils_dir = os.path.join(self.base_dir, "utils")

    def setup_directories(self):
        """Create all necessary directories for the project"""
        # Create templates directory
        os.makedirs(self.templates_dir, exist_ok=True)
        print(f"✓ Created templates directory at {self.templates_dir}")

        # Create utils directory
        os.makedirs(self.utils_dir, exist_ok=True)
        print(f"✓ Created utils directory at {self.utils_dir}")

        # Create static directory and subdirectories
        static_subdirs = [
            "css",
            "js",
            "img",
            "css/components",
            "css/pages",
            "img/illustrations",
        ]

        for subdir in static_subdirs:
            dir_path = os.path.join(self.static_dir, subdir)
            os.makedirs(dir_path, exist_ok=True)

        print(f"✓ Created static directory structure at {self.static_dir}")

        return True

    def create_default_files(self):
        """Create any default files that should exist"""
        # Create an empty CSS file if it doesn't exist
        style_css_path = os.path.join(self.static_dir, "css", "style.css")
        if not os.path.exists(style_css_path):
            with open(style_css_path, "w") as f:
                f.write("/* Main HiveBuzz stylesheet */\n")
            print(f"✓ Created empty style.css file at {style_css_path}")

        # Create an empty __init__.py in utils to make it a proper package
        init_path = os.path.join(self.utils_dir, "__init__.py")
        if not os.path.exists(init_path):
            with open(init_path, "w") as f:
                f.write('"""HiveBuzz utility functions"""\n')
            print(f"✓ Created __init__.py at {init_path}")

        return True

    def move_template_files(self):
        """Move template files from root to templates directory"""
        template_files = ["landing.html", "toggle_switch.html"]
        moved_count = 0

        for file in template_files:
            source_path = os.path.join(self.base_dir, file)
            dest_path = os.path.join(self.templates_dir, file)

            if os.path.exists(source_path):
                # Copy the file to the templates directory
                shutil.copy2(source_path, dest_path)
                print(f"✓ Copied {file} to templates directory")
                moved_count += 1
            else:
                print(f"! Warning: {file} not found in root directory")

        if moved_count > 0:
            print(f"✓ {moved_count} template files moved successfully!")

        return moved_count > 0

    def check_project_structure(self):
        """Check if the project structure is correctly set up"""
        issues = []

        # Check templates directory
        if not os.path.exists(self.templates_dir):
            issues.append(f"Templates directory missing: {self.templates_dir}")

        # Check static directory
        if not os.path.exists(self.static_dir):
            issues.append(f"Static directory missing: {self.static_dir}")

        # Check for critical template files
        critical_templates = ["base.html", "landing.html"]
        for template in critical_templates:
            if not os.path.exists(os.path.join(self.templates_dir, template)):
                issues.append(f"Critical template missing: {template}")

        # Check for critical static files
        css_path = os.path.join(self.static_dir, "css", "style.css")
        if not os.path.exists(css_path):
            issues.append(f"Critical CSS file missing: {css_path}")

        if issues:
            print("❌ Project structure check found issues:")
            for issue in issues:
                print(f"  - {issue}")
            return False

        print("✓ Project structure checks passed!")
        return True

    def run_complete_setup(self):
        """Run a complete setup of the project structure"""
        print("Starting HiveBuzz project setup...")

        # Set up directories
        self.setup_directories()

        # Create default files
        self.create_default_files()

        # Move template files
        self.move_template_files()

        # Check project structure
        if self.check_project_structure():
            print("\n✅ Setup completed successfully!")
        else:
            print("\n⚠️ Setup completed with warnings. Please check the issues above.")

        return True


# Execute setup when run directly
if __name__ == "__main__":
    setup = HiveBuzzSetup()
    setup.run_complete_setup()
