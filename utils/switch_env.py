"""
Environment Switcher for HiveBuzz
Utility script to switch between local and production environments
"""

import os
import re
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


def switch_environment(env_type: str) -> bool:
    """
    Switch environment configuration in .env file

    Args:
        env_type: 'local' or 'production'

    Returns:
        Boolean indicating success
    """
    if env_type not in ["local", "production"]:
        logger.error(f"Invalid environment type: {env_type}")
        return False

    env_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")

    if not os.path.exists(env_file_path):
        logger.error(f".env file not found at {env_file_path}")
        return False

    # Define the pairs of settings to toggle
    toggle_settings = [
        {
            "local": "APP_URL=http://localhost:5000",
            "production": "APP_URL=https://vkrishna04.pythonanywhere.com",
        },
        {
            "local": "HIVESIGNER_REDIRECT_URI=http://localhost:5000/hivesigner/callback",
            "production": "HIVESIGNER_REDIRECT_URI=https://vkrishna04.pythonanywhere.com/hivesigner/callback",
        },
    ]

    try:
        # Read current .env file
        with open(env_file_path, "r") as file:
            env_content = file.read()

        # Process each toggle setting
        for setting in toggle_settings:
            # Uncomment the desired environment's setting
            env_content = env_content.replace(
                f"# {setting[env_type]}", setting[env_type]
            )

            # Comment out the other environment's setting
            other_env = "production" if env_type == "local" else "local"
            if setting[other_env] in env_content:
                env_content = env_content.replace(
                    setting[other_env], f"# {setting[other_env]}"
                )

        # Write modified content back to file
        with open(env_file_path, "w") as file:
            file.write(env_content)

        logger.info(f"Successfully switched to {env_type} environment")
        return True

    except Exception as e:
        logger.exception(f"Error switching environment: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    import sys

    if len(sys.argv) != 2 or sys.argv[1] not in ["local", "production"]:
        print("Usage: python switch_env.py [local|production]")
        sys.exit(1)

    env_type = sys.argv[1]
    if switch_environment(env_type):
        print(f"Successfully switched to {env_type} environment")
    else:
        print(f"Failed to switch to {env_type} environment")
        sys.exit(1)
