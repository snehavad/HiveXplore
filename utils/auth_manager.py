"""
Authentication Manager for HiveBuzz
Handles user authentication, authorization, and session management
"""

import functools
import logging
from flask import redirect, url_for, session, flash, request


class AuthManager:
    """
    Authentication and session management for HiveBuzz application
    """

    def __init__(self, app=None):
        """Initialize with Flask app"""
        self.app = app
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app

        # Register a teardown function to cleanup any resources
        @app.teardown_appcontext
        def teardown_auth_manager(exception=None):
            pass  # Any cleanup code here if needed

    def login_user(self, username):
        """
        Log in a user by setting session variables

        Args:
            username: The Hive username of the user
        """
        session["username"] = username
        session.permanent = True  # Make the session persistent

    def logout_user(self):
        """Clear all user session data"""
        session.clear()

    def get_current_user(self):
        """Get the current logged-in user's username"""
        return session.get("username")

    def is_authenticated(self):
        """Check if a user is authenticated"""
        return "username" in session

    def require_login(self, view_func):
        """
        Decorator to require login for views
        Redirects to login page if user is not authenticated

        Args:
            view_func: The view function to decorate
        """

        @functools.wraps(view_func)
        def decorated_view(*args, **kwargs):
            if not self.is_authenticated():
                flash("Please log in to access this page.", "warning")
                return redirect(url_for("login", next=request.path))
            return view_func(*args, **kwargs)

        return decorated_view

    def save_user_preference(self, username, key, value):
        """
        Save a user preference

        Args:
            username: The username of the user
            key: Preference key
            value: Preference value
        """
        # Example implementation - would typically save to database
        if not username:
            return False

        # In a real app, save to database
        # For now, just update the session
        if key == "dark_mode":
            session["dark_mode"] = value
        elif key == "theme_color":
            session["theme_color"] = value

        return True

    def handle_login_redirect(self):
        """
        Handle redirection after successful login
        Returns the URL to redirect to after login
        """
        # Check for explicit next parameter
        next_url = request.args.get("next")

        # Validate next URL to prevent open redirect vulnerability
        if next_url and next_url.startswith("/") and not next_url.startswith("//"):
            return next_url

        # Default: redirect to dashboard if logged in
        return url_for("index")
