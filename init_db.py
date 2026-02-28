import logging

import database as db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def initialize_database():
    """Initialize the database with required tables"""
    conn = db.get_db_connection()
    try:
        cursor = conn.cursor()

        # Create comments table if it doesn't exist
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author TEXT NOT NULL,
            permlink TEXT NOT NULL,
            parent_author TEXT NOT NULL,
            parent_permlink TEXT NOT NULL,
            body TEXT NOT NULL,
            created TEXT,
            is_demo INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(author, permlink)
        )
        """
        )

        # Create index for faster comment retrieval
        cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_comments_parent
        ON comments (parent_author, parent_permlink)
        """
        )

        conn.commit()
        logger.info("Database initialized successfully")

    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    initialize_database()
    logger.info("Database initialization completed")
