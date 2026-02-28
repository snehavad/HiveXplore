"""
Setup Script for HiveBuzz

This script:
1. Creates necessary directories
2. Initializes the database
3. Sets up example data
4. Checks for required dependencies
"""

import os
import sys
import shutil
import logging
from pathlib import Path
import subprocess

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_python_version():
    """Check if Python version is adequate"""
    if sys.version_info < (3, 8):
        logger.error("HiveBuzz requires Python 3.8+")
        return False
    return True


def check_dependencies():
    """Check if required python packages are installed"""
    required_packages = [
        'flask',
        'requests',
        'python-dotenv',
        'click',
    ]

    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        logger.warning(f"Missing required packages: {', '.join(missing_packages)}")
        logger.info("Installing missing packages...")

        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing_packages)
            logger.info("Packages installed successfully!")
        except subprocess.CalledProcessError:
            logger.error("Failed to install required packages")
            return False

    return True


def create_directories():
    """Create required directories if they don't exist"""
    directories = [
        'static/uploads',
        'static/img/user',
        'logs',
        'instance',
        'docs',
    ]

    for directory in directories:
        path = Path(directory)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {directory}")


def create_env_file():
    """Create .env file if it doesn't exist"""
    env_path = Path('.env')
    example_env_path = Path('.env.example')

    if not env_path.exists() and example_env_path.exists():
        shutil.copyfile(example_env_path, env_path)
        logger.info(f"Created .env file from .env.example")


def initialize_database():
    """Initialize the database"""
    try:
        import database as db
        db.init_db()
        logger.info("Database initialized")
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


def setup_assets():
    """Set up asset directories and files"""
    # Check for required SVG files
    svg_dirs = [
        'static/img/icons',
        'static/img/illustrations',
        'static/img/social'
    ]

    for directory in svg_dirs:
        path = Path(directory)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created SVG directory: {directory}")


def main():
    """Main setup function"""
    logger.info("Starting HiveBuzz setup...")

    # Check Python version
    if not check_python_version():
        return

    # Check dependencies
    if not check_dependencies():
        return

    # Create necessary directories
    create_directories()

    # Create .env file if needed
    create_env_file()

    # Initialize database
    if not initialize_database():
        return

    # Set up assets
    setup_assets()

    logger.info("Setup completed successfully!")
    logger.info("You can now run the application with 'flask run' or 'python app.py'")


if __name__ == "__main__":
    main()
