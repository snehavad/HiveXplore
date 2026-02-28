"""
Database test utility for HiveBuzz
Tests database operations and provides sample data
"""

import json
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path

import database as db
from session_manager import session_manager

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Sample data
SAMPLE_USERS = [
    {
        "username": "user1",
        "auth_method": "keychain",
        "profile": {
            "name": "User One",
            "about": "This is a test user for HiveBuzz.",
            "website": "https://hive.blog/@user1",
            "location": "Internet",
            "profile_image": "https://images.hive.blog/u/user1/avatar",
        },
    },
    {
        "username": "user2",
        "auth_method": "hivesigner",
        "profile": {
            "name": "User Two",
            "about": "Another test user for HiveBuzz.",
            "website": "https://hive.blog/@user2",
            "location": "Blockchain",
            "profile_image": "https://images.hive.blog/u/user2/avatar",
        },
    },
    {
        "username": "user3",
        "auth_method": "hiveauth",
        "profile": {
            "name": "User Three",
            "about": "Third test user for HiveBuzz.",
            "website": "https://hive.blog/@user3",
            "location": "DApps",
            "profile_image": "https://images.hive.blog/u/user3/avatar",
        },
    },
]

SAMPLE_POSTS = [
    {
        "author": "user1",
        "permlink": "test-post-1",
        "category": "test",
        "title": "Test Post 1",
        "body": "This is a test post for database functionality.",
        "created": datetime.now().isoformat(),
        "json_metadata": {"tags": ["test", "hivebuzz", "development"]},
    },
    {
        "author": "user2",
        "permlink": "test-post-2",
        "category": "testing",
        "title": "Test Post 2",
        "body": "Another test post for database functionality.",
        "created": datetime.now().isoformat(),
        "json_metadata": {"tags": ["test", "database", "sqlite"]},
    },
]


def test_user_operations():
    """Test user operations"""
    logger.info("Testing user operations...")

    # Create sample users
    for user in SAMPLE_USERS:
        user_id = db.create_or_update_user(
            user["username"], user["auth_method"], profile=user["profile"]
        )
        logger.info(f"Created user {user['username']} with ID {user_id}")

    # Verify users were created
    for user in SAMPLE_USERS:
        user_data = db.get_user(user["username"])
        assert user_data is not None, f"User {user['username']} not found"
        assert user_data["username"] == user["username"], "Username mismatch"
        assert user_data["auth_method"] == user["auth_method"], "Auth method mismatch"
        logger.info(f"Verified user {user['username']}")

    # Update user preferences
    preferences = {
        "theme_color": "purple",
        "dark_mode": 1,
        "language": "en",
        "custom_setting": "value",
    }

    success = db.save_user_preferences(SAMPLE_USERS[0]["username"], preferences)
    assert success, "Failed to save user preferences"
    logger.info(f"Updated preferences for {SAMPLE_USERS[0]['username']}")

    # Verify preferences were saved
    user_data = db.get_user(SAMPLE_USERS[0]["username"])
    assert (
        user_data is not None
    ), f"User {SAMPLE_USERS[0]['username']} not found after saving preferences"
    assert user_data.get("theme_color") == "purple", "Theme color not saved"
    assert user_data.get("dark_mode") == 1, "Dark mode not saved"

    logger.info("User operations tests passed ✓")


def test_session_operations():
    """Test session operations"""
    logger.info("Testing session operations...")

    # Create a test session
    username = SAMPLE_USERS[0]["username"]
    auth_method = SAMPLE_USERS[0]["auth_method"]

    session_data = session_manager.create_session(
        username=username,
        auth_method=auth_method,
        additional_data={"test": "value"},
        expires_days=1,
    )

    assert session_data is not None, "Failed to create session"
    assert session_data["username"] == username, "Session username mismatch"
    assert session_data["auth_method"] == auth_method, "Session auth method mismatch"
    assert "session_id" in session_data, "No session ID returned"

    session_id = session_data["session_id"]
    logger.info(f"Created session with ID {session_id}")

    # Validate session
    is_valid = session_manager.is_session_valid(session_id)
    assert is_valid, "Session should be valid"
    logger.info(f"Session {session_id} is valid")

    # Get session data
    retrieved_data = session_manager.get_session_data(session_id)
    assert retrieved_data is not None, "Failed to get session data"
    assert retrieved_data["session_id"] == session_id, "Session ID mismatch"
    assert "data" in retrieved_data, "No data field in session"
    assert (
        retrieved_data["data"].get("test") == "value"
    ), "Session data content mismatch"

    # Update session data
    updated = session_manager.update_session_data(
        session_id, {"test": "updated", "new": "field"}
    )
    assert updated, "Failed to update session data"

    # Verify update
    retrieved_data = session_manager.get_session_data(session_id)
    assert retrieved_data is not None, "Failed to retrieve updated session data"
    data_field = retrieved_data.get("data", {})
    assert data_field.get("test") == "updated", "Session data not updated"
    assert data_field.get("new") == "field", "New session data field not added"

    # Delete session
    deleted = session_manager.delete_session(session_id)
    assert deleted, "Failed to delete session"

    # Verify deletion
    is_valid = session_manager.is_session_valid(session_id)
    assert not is_valid, "Session should be deleted"

    logger.info("Session operations tests passed ✓")


def test_post_caching():
    """Test post caching operations"""
    logger.info("Testing post caching operations...")

    # Cache sample posts
    for post in SAMPLE_POSTS:
        success = db.cache_post(post["author"], post["permlink"], post)
        assert success, f"Failed to cache post {post['permlink']}"
        logger.info(f"Cached post {post['author']}/{post['permlink']}")

    # Retrieve cached posts
    for post in SAMPLE_POSTS:
        cached = db.get_cached_post(post["author"], post["permlink"])
        assert cached is not None, f"Failed to retrieve cached post {post['permlink']}"
        assert cached["title"] == post["title"], "Post title mismatch"
        assert cached["body"] == post["body"], "Post body mismatch"
        logger.info(f"Retrieved cached post {post['author']}/{post['permlink']}")

    logger.info("Post caching tests passed ✓")


def test_activity_logging():
    """Test activity logging"""
    logger.info("Testing activity logging...")

    # Log various activities for users
    activities = [
        ("user1", "page_view", {"page": "index"}),
        ("user1", "post_view", {"author": "user2", "permlink": "test-post-2"}),
        ("user2", "page_view", {"page": "wallet"}),
        ("user2", "transfer", {"to": "user3", "amount": "10 HIVE"}),
        ("user3", "auth", {"action": "login"}),
    ]

    for username, action_type, details in activities:
        success = db.log_user_activity(username, action_type, details)
        assert success, f"Failed to log activity for {username}"
        logger.info(f"Logged {action_type} activity for {username}")

    # Retrieve activities
    for username in ["user1", "user2", "user3"]:
        user_activities = db.get_user_activity(username, limit=5)
        assert len(user_activities) > 0, f"No activities found for {username}"

        # Check the most recent activity
        recent = user_activities[0]
        logger.info(f"Most recent activity for {username}: {recent['action_type']}")

        # Verify details were saved correctly
        assert "details" in recent, "No details found in activity"
        assert recent["details"] is not None, "Activity details are None"

        # For page view activities, check the page
        if recent["action_type"] == "page_view":
            assert "page" in recent["details"], "No page in page_view details"

    logger.info("Activity logging tests passed ✓")


def run_all_tests():
    """Run all database tests"""
    try:
        # Initialize the database first
        db.init_db()
        logger.info("Database initialized for testing")

        # Run tests
        test_user_operations()
        test_session_operations()
        test_post_caching()
        test_activity_logging()

        logger.info("All database tests passed successfully! ✓")
    except AssertionError as e:
        logger.error(f"Test failed: {e}")
    except Exception as e:
        logger.error(f"Error during tests: {e}", exc_info=True)


if __name__ == "__main__":
    run_all_tests()
