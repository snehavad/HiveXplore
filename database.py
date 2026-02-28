"""
Database management module for HiveBuzz
Handles SQLite3 database connections and operations
"""

import json
import logging
import os
import sqlite3
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database file path
DATABASE_FILE = os.path.join(os.path.dirname(__file__), "hivebuzz.db")


def get_db_connection():
    """Create a connection to the SQLite database"""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row  # Enable row factory to access columns by name
    return conn


def init_db():
    """Initialize the database with required tables"""
    logger.info(f"Initializing database at {DATABASE_FILE}")

    if os.path.exists(DATABASE_FILE):
        logger.info("Database already exists")
        # Check if we need to update schema
        check_and_update_schema()
        return

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Create users table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            auth_method TEXT NOT NULL,
            last_login TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_demo BOOLEAN DEFAULT 0,
            profile TEXT  -- JSON field for profile data
        )
        """
        )

        # Create sessions table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            data TEXT,  -- JSON field for session data
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
        )

        # Create user preferences table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            theme_color TEXT DEFAULT 'blue',
            dark_mode BOOLEAN DEFAULT 0,
            display_nsfw BOOLEAN DEFAULT 0,
            language TEXT DEFAULT 'en',
            custom_css TEXT,
            additional_settings TEXT,  -- JSON field for other settings
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
        )

        # Create posts table (for post caching)
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS cached_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author TEXT NOT NULL,
            permlink TEXT NOT NULL,
            category TEXT,
            title TEXT,
            body TEXT,
            json_metadata TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cache_expires_at TIMESTAMP,
            UNIQUE(author, permlink)
        )
        """
        )

        # Create activity logs table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action_type TEXT NOT NULL,
            details TEXT,  -- JSON field for action details
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
        )

        # Insert default demo user
        cursor.execute(
            """
        INSERT INTO users (username, auth_method, last_login, is_demo, profile)
        VALUES (?, ?, ?, ?, ?)
        """,
            (
                "demo",
                "demo",
                datetime.now(),
                1,
                json.dumps(
                    {
                        "name": "Demo User",
                        "about": "This is a demo account for testing HiveBuzz features.",
                        "website": "https://hive.blog",
                        "location": "Blockchain",
                        "profile_image": "https://images.hive.blog/u/demo/avatar",
                    }
                ),
            ),
        )

        # Insert default preferences for demo user
        cursor.execute(
            """
        INSERT INTO user_preferences (user_id, theme_color, dark_mode)
        VALUES ((SELECT id FROM users WHERE username = 'demo'), ?, ?)
        """,
            ("blue", 0),
        )

        conn.commit()
        logger.info("Database successfully initialized")
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
        raise
    finally:
        conn.close()


def check_and_update_schema():
    """Check if database schema needs updates"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check if user_preferences table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_preferences'"
        )
        if not cursor.fetchone():
            logger.info("Adding user_preferences table")
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                theme_color TEXT DEFAULT 'blue',
                dark_mode BOOLEAN DEFAULT 0,
                display_nsfw BOOLEAN DEFAULT 0,
                language TEXT DEFAULT 'en',
                custom_css TEXT,
                additional_settings TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
            )

        # Check for other necessary schema updates
        # Add more schema update checks as needed

        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Schema update error: {e}")
        raise
    finally:
        conn.close()


# User management functions
def get_user(username):
    """Get user by username"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
        SELECT users.*, user_preferences.*
        FROM users
        LEFT JOIN user_preferences ON users.id = user_preferences.user_id
        WHERE username = ?
        """,
            (username,),
        )

        row = cursor.fetchone()
        if row:
            # Convert row to dictionary
            user_data = dict(row)
            # Parse JSON fields
            if user_data.get("profile"):
                user_data["profile"] = json.loads(user_data["profile"])
            if user_data.get("additional_settings"):
                user_data["additional_settings"] = json.loads(
                    user_data["additional_settings"]
                )
            return user_data
        return None
    finally:
        conn.close()


def create_or_update_user(username, auth_method, profile=None, is_demo=False):
    """Create a new user or update existing one"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Try to find existing user
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if profile and isinstance(profile, dict):
            profile_json = json.dumps(profile)
        else:
            profile_json = None

        if user:
            # Update existing user
            cursor.execute(
                """
            UPDATE users
            SET auth_method = ?, last_login = ?, is_demo = ?, profile = COALESCE(?, profile)
            WHERE username = ?
            """,
                (auth_method, datetime.now(), is_demo, profile_json, username),
            )
            user_id = user["id"]
        else:
            # Create new user
            cursor.execute(
                """
            INSERT INTO users (username, auth_method, last_login, is_demo, profile)
            VALUES (?, ?, ?, ?, ?)
            """,
                (username, auth_method, datetime.now(), is_demo, profile_json),
            )
            user_id = cursor.lastrowid

            # Create default preferences for new user
            cursor.execute(
                """
            INSERT INTO user_preferences (user_id, theme_color, dark_mode)
            VALUES (?, ?, ?)
            """,
                (user_id, "blue", 0),
            )

        conn.commit()
        return user_id
    except sqlite3.Error as e:
        logger.error(f"Error creating/updating user: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def save_user_preferences(username, preferences):
    """Save user preferences"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get user ID
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if not user:
            return False

        user_id = user["id"]

        # Extract known preference fields
        theme_color = preferences.get("theme_color")
        dark_mode = preferences.get("dark_mode", 0)
        display_nsfw = preferences.get("display_nsfw", 0)
        language = preferences.get("language")
        custom_css = preferences.get("custom_css")

        # Store additional settings as JSON
        additional_settings = {
            k: v
            for k, v in preferences.items()
            if k
            not in [
                "theme_color",
                "dark_mode",
                "display_nsfw",
                "language",
                "custom_css",
            ]
        }

        additional_settings_json = (
            json.dumps(additional_settings) if additional_settings else None
        )

        # Update preferences
        cursor.execute(
            """
        UPDATE user_preferences
        SET theme_color = COALESCE(?, theme_color),
            dark_mode = COALESCE(?, dark_mode),
            display_nsfw = COALESCE(?, display_nsfw),
            language = COALESCE(?, language),
            custom_css = COALESCE(?, custom_css),
            additional_settings = COALESCE(?, additional_settings)
        WHERE user_id = ?
        """,
            (
                theme_color,
                dark_mode,
                display_nsfw,
                language,
                custom_css,
                additional_settings_json,
                user_id,
            ),
        )

        if cursor.rowcount == 0:
            # Insert if no row existed
            cursor.execute(
                """
            INSERT INTO user_preferences (user_id, theme_color, dark_mode, display_nsfw, language, custom_css, additional_settings)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    user_id,
                    theme_color,
                    dark_mode,
                    display_nsfw,
                    language,
                    custom_css,
                    additional_settings_json,
                ),
            )

        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error saving user preferences: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def log_user_activity(username, action_type, details=None):
    """Log user activity"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get user ID
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if not user:
            return False

        user_id = user["id"]
        details_json = json.dumps(details) if details else None

        cursor.execute(
            """
        INSERT INTO activity_logs (user_id, action_type, details)
        VALUES (?, ?, ?)
        """,
            (user_id, action_type, details_json),
        )

        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error logging user activity: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_user_activity(username, limit=10):
    """Get user activity logs"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
        SELECT activity_logs.*
        FROM activity_logs
        JOIN users ON activity_logs.user_id = users.id
        WHERE users.username = ?
        ORDER BY activity_logs.created_at DESC
        LIMIT ?
        """,
            (username, limit),
        )

        activities = []
        for row in cursor.fetchall():
            activity = dict(row)
            if activity.get("details"):
                activity["details"] = json.loads(activity["details"])
            activities.append(activity)

        return activities
    finally:
        conn.close()


def cache_post(author, permlink, post_data, expires_in_hours=24):
    """Cache a post in the database"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        expires_at = datetime.now().timestamp() + (expires_in_hours * 3600)
        json_metadata = json.dumps(post_data.get("json_metadata", {}))

        cursor.execute(
            """
        INSERT OR REPLACE INTO cached_posts
        (author, permlink, category, title, body, json_metadata, created_at, updated_at, cache_expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
        """,
            (
                author,
                permlink,
                post_data.get("category"),
                post_data.get("title"),
                post_data.get("body"),
                json_metadata,
                post_data.get("created"),
                expires_at,
            ),
        )

        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error caching post: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_cached_post(author, permlink):
    """Get a cached post if available and not expired"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        current_time = datetime.now().timestamp()
        cursor.execute(
            """
        SELECT * FROM cached_posts
        WHERE author = ? AND permlink = ? AND cache_expires_at > ?
        """,
            (author, permlink, current_time),
        )

        row = cursor.fetchone()
        if row:
            post = dict(row)
            if post.get("json_metadata"):
                post["json_metadata"] = json.loads(post["json_metadata"])
            return post
        return None
    finally:
        conn.close()


def cache_comment(comment_data):
    """
    Cache a comment in the database

    Args:
        comment_data: Dictionary with comment data

    Returns:
        True if successful, False otherwise
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Check if this comment already exists
        author = comment_data.get("author")
        permlink = comment_data.get("permlink")

        cursor.execute(
            "SELECT id FROM comments WHERE author = ? AND permlink = ?",
            (author, permlink),
        )
        existing = cursor.fetchone()

        if existing:
            # Update existing comment
            cursor.execute(
                """
                UPDATE comments
                SET parent_author = ?, parent_permlink = ?, body = ?,
                    created = ?, is_demo = ?, updated_at = CURRENT_TIMESTAMP
                WHERE author = ? AND permlink = ?
                """,
                (
                    comment_data.get("parent_author"),
                    comment_data.get("parent_permlink"),
                    comment_data.get("body"),
                    comment_data.get("created"),
                    comment_data.get("is_demo", 0),
                    author,
                    permlink,
                ),
            )
        else:
            # Insert new comment
            cursor.execute(
                """
                INSERT INTO comments
                (author, permlink, parent_author, parent_permlink, body,
                created, is_demo, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (
                    author,
                    permlink,
                    comment_data.get("parent_author"),
                    comment_data.get("parent_permlink"),
                    comment_data.get("body"),
                    comment_data.get("created"),
                    comment_data.get("is_demo", 0),
                ),
            )

        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error caching comment: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_comments_for_post(author, permlink):
    """
    Get comments for a specific post from the database

    Args:
        author: Post author
        permlink: Post permlink

    Returns:
        List of comment dictionaries
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Get all comments for this post
        cursor.execute(
            """
            SELECT * FROM comments
            WHERE parent_author = ? AND parent_permlink = ?
            ORDER BY created DESC
            """,
            (author, permlink),
        )

        # Convert to list of dictionaries
        comments = []
        columns = [column[0] for column in cursor.description]
        for row in cursor.fetchall():
            comment = dict(zip(columns, row))
            # Convert boolean fields
            comment["is_demo"] = bool(comment.get("is_demo", 0))
            comments.append(comment)

        return comments
    except Exception as e:
        logger.error(f"Error fetching comments for post {author}/{permlink}: {e}")
        return []
    finally:
        conn.close()


# Initialize database when module is imported
try:
    init_db()
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")
