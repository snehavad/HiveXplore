"""
Configuration management for HiveBuzz application
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()


class Config:
    """Base configuration"""

    SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key-replace-in-production")
    DEBUG = False
    TESTING = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_TYPE = "filesystem"
    SESSION_PERMANENT = True

    # Application URLs
    APP_URL = os.getenv("APP_URL", "https://hivebuzz.onrender.com")

    # HiveSigner Configuration
    HIVESIGNER_APP_NAME = os.getenv("HIVESIGNER_APP_NAME", "HiveBuzz")
    HIVESIGNER_CLIENT_SECRET = os.getenv("HIVESIGNER_CLIENT_SECRET", "")
    HIVESIGNER_APP_HOST = os.getenv("HIVESIGNER_APP_HOST", "https://hivesigner.com")
    HIVESIGNER_REDIRECT_URI = os.getenv(
        "HIVESIGNER_REDIRECT_URI",
        "https://hivebuzz.onrender.com/hivesigner/callback",
    )
    HIVESIGNER_SCOPE = os.getenv("HIVESIGNER_SCOPE", "login")


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True
    TESTING = True


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False
    TESTING = False
    # In production, ensure you have a strong secret key
    SECRET_KEY = os.getenv("SECRET_KEY")
    # Use more secure session settings in production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class TestingConfig(DevelopmentConfig):
    """Testing configuration"""

    TESTING = True


def get_config():
    """Return the appropriate configuration based on environment"""
    env = os.getenv("FLASK_ENV", "development").lower()

    if env == "production":
        return ProductionConfig
    elif env == "testing":
        return TestingConfig
    else:
        return DevelopmentConfig
