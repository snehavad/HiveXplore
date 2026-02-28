"""
Database Manager utility for HiveBuzz
Provides command-line interface for database operations
"""

import sys
import time
import click
import logging
from pathlib import Path
from datetime import datetime, timedelta
import database as db
from session_manager import session_manager

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Database management utilities for HiveBuzz"""
    pass


@cli.command()
def init():
    """Initialize the database"""
    try:
        db.init_db()
        click.echo("Database initialized successfully!")
    except Exception as e:
        click.echo(f"Error initializing database: {e}", err=True)
        sys.exit(1)


@cli.command()
def stats():
    """Show database statistics"""
    try:
        conn = db.get_db_connection()
        cursor = conn.cursor()

        click.echo("Database Statistics:")
        click.echo("-" * 40)

        # Users stats
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        click.echo(f"Total users: {user_count}")

        # Demo users
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_demo = 1")
        demo_count = cursor.fetchone()[0]
        click.echo(f"Demo users: {demo_count}")

        # Active sessions
        cursor.execute(
            "SELECT COUNT(*) FROM sessions WHERE expires_at > datetime('now')"
        )
        active_sessions = cursor.fetchone()[0]
        click.echo(f"Active sessions: {active_sessions}")

        # Expired sessions
        cursor.execute(
            "SELECT COUNT(*) FROM sessions WHERE expires_at <= datetime('now')"
        )
        expired_sessions = cursor.fetchone()[0]
        click.echo(f"Expired sessions: {expired_sessions}")

        # Cached posts
        cursor.execute("SELECT COUNT(*) FROM cached_posts")
        cached_posts = cursor.fetchone()[0]
        click.echo(f"Cached posts: {cached_posts}")

        # Activity logs
        cursor.execute("SELECT COUNT(*) FROM activity_logs")
        activity_logs = cursor.fetchone()[0]
        click.echo(f"Activity logs: {activity_logs}")

        # Database size
        db_path = Path(db.DATABASE_FILE)
        if db_path.exists():
            db_size = db_path.stat().st_size / (1024 * 1024)  # Size in MB
            click.echo(f"Database size: {db_size:.2f} MB")

        # Last activities
        click.echo("\nLast 5 activities:")
        cursor.execute(
            """
        SELECT users.username, activity_logs.action_type, activity_logs.created_at
        FROM activity_logs
        JOIN users ON activity_logs.user_id = users.id
        ORDER BY activity_logs.created_at DESC
        LIMIT 5
        """
        )
        activities = cursor.fetchall()
        for act in activities:
            click.echo(f"- {act[0]} | {act[1]} | {act[2]}")

    except Exception as e:
        click.echo(f"Error getting database statistics: {e}", err=True)
    finally:
        conn.close()


@cli.command()
def clear_sessions():
    """Clear expired sessions"""
    try:
        count = session_manager.clear_expired_sessions()
        click.echo(f"Cleared {count} expired sessions")
    except Exception as e:
        click.echo(f"Error clearing sessions: {e}", err=True)


@cli.command()
@click.argument("username")
def user_info(username):
    """Show information about a specific user"""
    try:
        user_data = db.get_user(username)
        if user_data:
            click.echo(f"User Information for @{username}:")
            click.echo("-" * 40)
            click.echo(f"Authentication Method: {user_data.get('auth_method')}")
            click.echo(f"Created At: {user_data.get('created_at')}")
            click.echo(f"Last Login: {user_data.get('last_login')}")
            click.echo(f"Is Demo: {'Yes' if user_data.get('is_demo') else 'No'}")

            click.echo("\nPreferences:")
            click.echo(f"Theme Color: {user_data.get('theme_color', 'default')}")
            click.echo(
                f"Dark Mode: {'Enabled' if user_data.get('dark_mode') else 'Disabled'}"
            )

            # Get user activity
            conn = db.get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
            SELECT action_type, created_at
            FROM activity_logs
            JOIN users ON activity_logs.user_id = users.id
            WHERE users.username = ?
            ORDER BY created_at DESC
            LIMIT 5
            """,
                (username,),
            )

            activities = cursor.fetchall()
            if activities:
                click.echo("\nRecent Activities:")
                for act in activities:
                    click.echo(f"- {act[0]} | {act[1]}")

            conn.close()
        else:
            click.echo(f"User '{username}' not found")
    except Exception as e:
        click.echo(f"Error retrieving user info: {e}", err=True)


@cli.command()
@click.option("--days", default=30, help="Number of days of data to keep")
def cleanup(days):
    """Cleanup old data from the database"""
    try:
        conn = db.get_db_connection()
        cursor = conn.cursor()

        # Clean up old activity logs
        cursor.execute(
            """
        DELETE FROM activity_logs
        WHERE created_at < datetime('now', ? || ' days')
        """,
            (f"-{days}",),
        )
        activities_removed = cursor.rowcount

        # Clean up expired cached posts
        cursor.execute(
            """
        DELETE FROM cached_posts
        WHERE cache_expires_at < datetime('now')
        """
        )
        posts_removed = cursor.rowcount

        # Clean up expired sessions
        cursor.execute(
            """
        DELETE FROM sessions
        WHERE expires_at < datetime('now')
        """
        )
        sessions_removed = cursor.rowcount

        conn.commit()
        conn.close()

        click.echo(f"Cleanup complete:")
        click.echo(f"- {activities_removed} activity logs removed")
        click.echo(f"- {posts_removed} cached posts removed")
        click.echo(f"- {sessions_removed} expired sessions removed")

    except Exception as e:
        click.echo(f"Error during cleanup: {e}", err=True)


@cli.command()
def vacuum():
    """Vacuum the database to optimize storage"""
    try:
        conn = db.get_db_connection()
        cursor = conn.cursor()

        # Get size before vacuum
        db_path = Path(db.DATABASE_FILE)
        size_before = db_path.stat().st_size / (1024 * 1024)  # Size in MB

        # Execute vacuum
        click.echo("Running VACUUM operation...")
        start_time = time.time()
        cursor.execute("VACUUM")
        end_time = time.time()

        # Get size after vacuum
        size_after = db_path.stat().st_size / (1024 * 1024)

        click.echo(f"VACUUM completed in {end_time - start_time:.2f} seconds")
        click.echo(f"Size before: {size_before:.2f} MB")
        click.echo(f"Size after: {size_after:.2f} MB")
        click.echo(
            f"Space saved: {size_before - size_after:.2f} MB ({(1 - size_after/size_before) * 100:.1f}%)"
        )

    except Exception as e:
        click.echo(f"Error during VACUUM: {e}", err=True)
    finally:
        conn.close()


@cli.command()
@click.argument("username")
@click.argument("auth_method")
@click.option("--demo/--no-demo", default=False, help="Mark as demo user")
def add_user(username, auth_method, demo):
    """Add a new user manually"""
    try:
        user_id = db.create_or_update_user(username, auth_method, is_demo=demo)
        if user_id:
            click.echo(f"User '{username}' created successfully with ID {user_id}")
        else:
            click.echo("Failed to create user", err=True)
    except Exception as e:
        click.echo(f"Error creating user: {e}", err=True)


@cli.command()
@click.argument("output_file", default="hivebuzz_backup.sql")
def backup(output_file):
    """Backup the database to a SQL file"""
    try:
        conn = db.get_db_connection()

        with open(output_file, "w") as f:
            for line in conn.iterdump():
                f.write(f"{line}\n")

        click.echo(f"Database backed up to {output_file}")
        conn.close()
    except Exception as e:
        click.echo(f"Error backing up database: {e}", err=True)


if __name__ == "__main__":
    cli()
