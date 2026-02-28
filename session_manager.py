"""
Session management module for HiveBuzz
Handles session storage, creation, and validation
"""

import json
import logging
import sqlite3
import time
import uuid
from datetime import datetime, timedelta

import database as db

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SessionManager:
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
        # Set up before_request handler to validate sessions
        app.before_request(self.validate_session)

    def validate_session(self):
        """Validate the current session"""
        from flask import redirect, request, session, url_for

        # Skip validation for login/logout routes
        if request.endpoint in ("login", "logout", "static"):
            return

        if "username" in session and "session_id" in session:
            # Check if session is still valid
            if not self.is_session_valid(session["session_id"]):
                logger.warning(
                    f"Invalid session for {session['username']}, redirecting to login"
                )
                session.clear()
                return redirect(url_for("login"))

    def create_session(
        self, username, auth_method, additional_data=None, expires_days=7
    ):
        """Create a new session in the database"""
        conn = db.get_db_connection()
        cursor = conn.cursor()

        try:
            # Get user ID
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()

            if not user:
                logger.error(f"Cannot create session: User {username} not found")
                return None

            user_id = user["id"]
            session_id = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(days=expires_days)

            # Store additional data as JSON
            data_json = None
            if additional_data:
                data_json = json.dumps(additional_data)

            # Create session record
            cursor.execute(
                """
            INSERT INTO sessions (session_id, user_id, expires_at, data)
            VALUES (?, ?, ?, ?)
            """,
                (session_id, user_id, expires_at, data_json),
            )

            conn.commit()
            return {
                "session_id": session_id,
                "username": username,
                "auth_method": auth_method,
                "expires_at": expires_at,
            }
        except sqlite3.Error as e:
            logger.error(f"Error creating session: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()

    def is_session_valid(self, session_id):
        """Check if a session is valid and not expired"""
        conn = db.get_db_connection()
        cursor = conn.cursor()

        try:
            current_time = datetime.now()
            cursor.execute(
                """
            SELECT sessions.*, users.username
            FROM sessions
            JOIN users ON sessions.user_id = users.id
            WHERE sessions.session_id = ? AND sessions.expires_at > ?
            """,
                (session_id, current_time),
            )

            session = cursor.fetchone()
            return bool(session)
        except sqlite3.Error as e:
            logger.error(f"Error checking session validity: {e}")
            return False
        finally:
            conn.close()

    def get_session_data(self, session_id):
        """Get session data from database"""
        conn = db.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
            SELECT sessions.*, users.username, users.auth_method
            FROM sessions
            JOIN users ON sessions.user_id = users.id
            WHERE sessions.session_id = ?
            """,
                (session_id,),
            )

            session = cursor.fetchone()
            if not session:
                return None

            result = dict(session)

            # Parse JSON data if present
            if result.get("data"):
                result["data"] = json.loads(result["data"])

            return result
        except sqlite3.Error as e:
            logger.error(f"Error getting session data: {e}")
            return None
        finally:
            conn.close()

    def update_session_data(self, session_id, data):
        """Update session data"""
        conn = db.get_db_connection()
        cursor = conn.cursor()

        try:
            data_json = json.dumps(data)

            cursor.execute(
                """
            UPDATE sessions
            SET data = ?
            WHERE session_id = ?
            """,
                (data_json, session_id),
            )

            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error updating session data: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def delete_session(self, session_id):
        """Delete a session from the database"""
        conn = db.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error deleting session: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def clear_expired_sessions(self):
        """Remove expired sessions from the database"""
        conn = db.get_db_connection()
        cursor = conn.cursor()

        try:
            current_time = datetime.now()
            cursor.execute("DELETE FROM sessions WHERE expires_at < ?", (current_time,))

            deleted_count = cursor.rowcount
            conn.commit()

            if deleted_count > 0:
                logger.info(f"Cleared {deleted_count} expired sessions")

            return deleted_count
        except sqlite3.Error as e:
            logger.error(f"Error clearing expired sessions: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()


# Create a global instance
session_manager = SessionManager()
