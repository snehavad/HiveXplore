"""
WSGI entry point for HiveBuzz application
For hosting on PythonAnywhere or similar services
"""

import logging
import os
import sys
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

# Import your app and other necessary modules
from app import app as hivebuzz_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the application directory to the Python path
app_dir = os.path.dirname(os.path.abspath(__file__))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

# Create the Flask application
app = Flask(__name__)

# Apply ProxyFix to handle reverse proxy setups (if needed)
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1
)

# Set the harakiri timeout programmatically
os.environ["UWSGI_HARAKIRI"] = "60"

# Initialize the HiveBuzz app
app = hivebuzz_app

# Add error handling for initialization
try:
    # Initialize components here
    logger.info("HiveBuzz application initialized successfully.")
except Exception as e:
    logger.exception("Error during HiveBuzz application initialization: %s", e)


# Define a simple health check endpoint
@app.route("/health")
def health_check():
    return "OK", 200


# Add error handling for requests
@app.errorhandler(Exception)
def handle_exception(e):
    logger.exception("Unhandled exception: %s", e)
    return "Internal Server Error", 500


# Log startup information
logger.info(f"Starting HiveBuzz WSGI application from {app_dir}")

# For PythonAnywhere or any WSGI server
if __name__ == "__main__":
    # Run the application
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
