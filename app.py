import atexit
import json
import logging
import os
import time
from datetime import datetime, timezone
from functools import wraps

import bleach

# Add imports for markdown processing
import markdown
from dotenv import load_dotenv
from flask import (
    Blueprint,
    Flask,
    Response,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    stream_with_context,
    url_for,
)
from markupsafe import Markup
from slugify import slugify as slugify_function  # Make sure to install python-slugify

import database as db  # Import our database module
from config import get_config
from session_manager import session_manager  # Import our session manager
from utils.auth_manager import AuthManager  # Import auth manager

# Import required modules
from utils.hive_api import _beem_available, get_hive_api
from utils.hiveauth import init_hiveauth

# Import our HiveSigner and HiveAuth utils
from utils.hivesigner import get_hivesigner_client, init_hivesigner

# Register markdown filter using our utility
from utils.markdown_utils import setup_markdown_filter

# Add the new posts cache
from utils.posts_cache import get_posts_cache, init_posts_cache  # noqa: F401

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get config based on environment
config = get_config()

app = Flask(__name__)
app.config.from_object(config)


setup_markdown_filter(app)

# Add additional configuration from .env file directly to app config
app.config["HIVESIGNER_APP_NAME"] = os.getenv("HIVESIGNER_APP_NAME", "HiveBuzz")
app.config["HIVESIGNER_REDIRECT_URI"] = os.getenv(
    "HIVESIGNER_REDIRECT_URI", "http://localhost:5000/hivesigner/callback"
)
app.config["HIVESIGNER_APP_HOST"] = os.getenv(
    "HIVESIGNER_APP_HOST", "https://hivesigner.com"
)
app.config["APP_URL"] = os.getenv("APP_URL", "http://localhost:5000")

# Define cache directory based on instance path
cache_dir = os.path.join(app.instance_path, "cache", "posts")
try:
    os.makedirs(cache_dir, exist_ok=True)
    logger.info(f"Using cache directory: {cache_dir}")
except Exception as e:
    logger.warning(f"Could not create cache directory {cache_dir}: {e}")
    # Fallback to temporary directory
    import tempfile

    cache_dir = os.path.join(tempfile.gettempdir(), "hivebuzz", "cache", "posts")
    os.makedirs(cache_dir, exist_ok=True)
    logger.info(f"Using fallback cache directory: {cache_dir}")

# Initialize session manager with the app
session_manager.init_app(app)

# Initialize auth manager
auth_manager = AuthManager(app)

# Initialize HiveSigner with app details from .env
hivesigner_app_name = app.config["HIVESIGNER_APP_NAME"]
hivesigner_client_secret = os.getenv("HIVESIGNER_CLIENT_SECRET", "")
init_hivesigner(hivesigner_app_name)  # Initialize with the app name as client ID

# Initialize HiveAuth with app details from .env
init_hiveauth(
    app_name=app.config["HIVESIGNER_APP_NAME"],
    app_description=f"{app.config['HIVESIGNER_APP_NAME']} - Explore the Hive blockchain",
    app_icon=f"{app.config['APP_URL']}/static/img/logo.svg",
)

# Initialize PostsCache with a 5-minute refresh interval (300 seconds)
posts_cache = init_posts_cache(refresh_interval=300)

# Remove or comment out blocking wait:
logger.info("Starting HiveBuzz without waiting for cached posts to load")
# priority_feeds_loaded = posts_cache.wait_for_initialization(timeout=5.0)
# if priority_feeds_loaded:
#     logger.info("Priority feeds loaded successfully")
# else:
#     logger.warning("Priority feeds loading timeout - continuing startup")


# Initialize HiveAPI on first access, not at startup
def get_initialized_api():
    """Get the HiveAPI instance and initiate its background initialization"""
    api = get_hive_api()
    # Start background initialization if not already started
    if not api.initializing and not api.initialized:
        # This starts the initialization in background without waiting
        api._ensure_initialization_started()
    return api


# No need to explicitly initialize blockchain at app start
# We'll initialize it on first access instead

# Demo data for non-authenticated views
DEMO_POSTS = [
    {
        "id": 1,
        "author": "demo",
        "permlink": "welcome-to-hivebuzz",
        "title": "Welcome to HiveBuzz",
        "body": "This is a demo post to show what HiveBuzz looks like. In a real deployment, this would be actual content from the Hive blockchain.",
        "created": "2023-05-15T10:30:00",
        "payout": "10.52",
        "tags": ["hivebuzz", "welcome", "demo"],
        "vote_count": 42,
        "comment_count": 7,
    },
    {
        "id": 2,
        "author": "demo",
        "permlink": "getting-started-with-hive",
        "title": "Getting Started with Hive Blockchain",
        "body": "Hive is a fast, scalable, and powerful blockchain built for Web 3.0. This post introduces you to the basics of Hive and how to get started.",
        "created": "2023-05-10T08:15:00",
        "payout": "25.75",
        "tags": ["hive", "blockchain", "crypto", "tutorial"],
        "vote_count": 67,
        "comment_count": 15,
    },
    {
        "id": 3,
        "author": "demo",
        "permlink": "hivebuzz-new-features",
        "title": "New Features in HiveBuzz",
        "body": "We are excited to announce several new features in HiveBuzz including improved wallet integration, better post discovery, and enhanced social features.",
        "created": "2023-05-05T14:45:00",
        "payout": "18.34",
        "tags": ["hivebuzz", "update", "features"],
        "vote_count": 53,
        "comment_count": 9,
    },
]


# Authentication required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            flash("You need to be logged in to view this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


@app.before_request
def load_user():
    """Load user data into g if logged in"""
    if "username" in session:
        g.user = db.get_user(session["username"])
    else:
        g.user = None


@app.route("/")
def index():
    """Homepage route"""
    if "username" in session:
        # Get real user data from the database
        username = session["username"]
        user_data = db.get_user(username) or {}

        # Log this page visit
        db.log_user_activity(username, "page_view", {"page": "index"})

        # Get user activity for the dashboard
        activity = db.get_user_activity(username, limit=5)
        formatted_activity = []

        for item in activity:
            if item["action_type"] == "page_view":
                page = item["details"].get("page", "unknown")
                formatted_activity.append(
                    {
                        "type": "view",
                        "title": f"Viewed {page} page",
                        "time": item["created_at"],
                        "link": f"/{page}" if page != "index" else "/",
                    }
                )
            elif item["action_type"] == "post_view":
                formatted_activity.append(
                    {
                        "type": "post",
                        "title": f'Viewed post: {item["details"].get("title", "Untitled")}',
                        "time": item["created_at"],
                        "link": f'/post/{item["details"].get("author")}/{item["details"].get("permlink")}',
                    }
                )
            elif item["action_type"] == "auth":
                formatted_activity.append(
                    {
                        "type": "auth",
                        "title": f'Authentication: {item["details"].get("action", "login")}',
                        "time": item["created_at"],
                    }
                )

        # Fetch trending posts from cache instead of direct API call
        try:
            # Get cached trending posts - now get more to allow scrolling
            trending_posts = posts_cache.get_posts(feed_type="trending", limit=10)

            # Ensure we have posts - otherwise use demo data
            if not trending_posts:
                logger.warning(
                    "No posts returned from cache for dashboard, using demo data"
                )
                trending_posts = DEMO_POSTS

            # Ensure posts have necessary fields
            for post in trending_posts:
                # Clean up post body and ensure it's not too long
                if "body" in post and post["body"]:
                    post["body"] = post["body"][:500]  # Limit the initial content size

                # Make sure created date is formatted consistently
                if "created" in post:
                    if isinstance(post["created"], str):
                        # Keep string as is
                        pass
                    elif hasattr(post["created"], "strftime"):
                        # Convert datetime to string
                        post["created"] = post["created"].strftime("%Y-%m-%d")
                    else:
                        post["created"] = "Recent"  # Add default when format is unknown

                # Ensure other required fields have defaults
                post["comment_count"] = post.get("comment_count", 0)
                post["vote_count"] = post.get("vote_count", 0)
                post["payout"] = post.get("payout", "0.00")

        except Exception as e:
            logger.error(f"Failed to fetch trending posts from cache: {e}")
            # Fallback to demo data if cache lookup fails
            trending_posts = DEMO_POSTS

        # Use real blockchain data for non-demo users
        stats = {}
        is_demo = username == "demo" or user_data.get("is_demo", False)

        if is_demo:
            # Use demo data for demo users
            stats = {
                "wallet": {"hive": "100.000", "hp": "5000.000", "hbd": "250.000"},
                "reputation": "72",
                "followers": 256,
                "following": 128,
                "posts_count": 42,
            }
        else:
            # Get real blockchain data for non-demo users
            try:
                # Get Hive API client
                hive_api_client = get_hive_api()

                # Get wallet data
                wallet_data = hive_api_client.get_user_wallet(username)

                # Get profile stats
                profile_data = hive_api_client.get_user_profile(username)

                # Compile stats from real data
                stats = {
                    "wallet": {
                        "hive": wallet_data.get("hive_balance", "0.0000"),
                        "hp": wallet_data.get("hive_power", "0.0000"),
                        "hbd": wallet_data.get("hbd_balance", "0.0000"),
                    },
                    "reputation": profile_data.get("reputation", "0"),  # type: ignore
                    "followers": profile_data.get("followers_count", 0),  # type: ignore
                    "following": profile_data.get("following_count", 0),  # type: ignore
                    "posts_count": profile_data.get("post_count", 0),  # type: ignore
                }
            except Exception as e:
                logger.warning(f"Error fetching blockchain data for {username}: {e}")
                # Fallback to placeholder data on error
                stats = {
                    "wallet": {"hive": "0.000", "hp": "0.000", "hbd": "0.000"},
                    "reputation": "0",
                    "followers": 0,
                    "following": 0,
                    "posts_count": 0,
                }

        return render_template(
            "dashboard.html",
            user=user_data,
            stats=stats,
            activity=formatted_activity,
            trending=trending_posts,
            is_demo=is_demo,
        )
    else:
        # Show landing page for non-authenticated users
        return render_template("landing.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login route"""
    # If user is already logged in, redirect to dashboard
    if "username" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        # Handle keychain login
        if request.form.get("login_method") == "keychain":
            username = request.form.get("username")
            signature = request.form.get("signature")
            challenge = request.form.get("challenge")

            # In a real app, you would verify the signature here
            # For demo purposes, we're just accepting it

            # Create or update user in database
            user_id = db.create_or_update_user(username, "keychain")

            if user_id:
                # Create a new session
                session_data = session_manager.create_session(
                    username=username,
                    auth_method="keychain",
                    additional_data={"challenge": challenge, "signature": signature},
                )

                if session_data:
                    # Set Flask session variables
                    session["username"] = username
                    session["auth_method"] = "keychain"
                    session["session_id"] = session_data["session_id"]

                    # Load user preferences from database
                    user_data = db.get_user(username)
                    if user_data:
                        if user_data.get("dark_mode") is not None:
                            session["dark_mode"] = bool(user_data.get("dark_mode"))
                        if user_data.get("theme_color"):
                            session["theme_color"] = user_data.get("theme_color")

                    # Log activity
                    db.log_user_activity(
                        username, "auth", {"action": "login", "method": "keychain"}
                    )

                    flash("Successfully logged in with Hive Keychain!", "success")

                    # Get next URL from query parameter or default to dashboard
                    next_url = request.args.get("next")
                    if (
                        next_url
                        and next_url.startswith("/")
                        and not next_url.startswith("//")
                    ):
                        return redirect(next_url)
                    return redirect(url_for("index"))
                else:
                    flash("Failed to create user session.", "error")
            else:
                flash("Failed to create or update user.", "error")

        # Handle regular username login or demo login
        elif request.form.get("login_method") == "demo" or request.form.get("username"):
            username = request.form.get("username") or "demo"

            # Create or update user
            is_demo = username == "demo"
            user_id = db.create_or_update_user(
                username, "demo" if is_demo else "basic", is_demo=is_demo
            )

            if user_id:
                # Create a new session
                session_data = session_manager.create_session(
                    username=username,
                    auth_method="demo" if is_demo else "basic",
                    additional_data={"is_demo": is_demo},
                )

                if session_data:
                    # Set Flask session variables
                    session["username"] = username
                    session["auth_method"] = "demo" if is_demo else "basic"
                    session["session_id"] = session_data["session_id"]

                    # Load user preferences from database
                    user_data = db.get_user(username)
                    if user_data:
                        if user_data.get("dark_mode") is not None:
                            session["dark_mode"] = bool(user_data.get("dark_mode"))
                        if user_data.get("theme_color"):
                            session["theme_color"] = user_data.get("theme_color")

                    # Log activity
                    db.log_user_activity(
                        username,
                        "auth",
                        {"action": "login", "method": "demo" if is_demo else "basic"},
                    )

                    message = (
                        "You are now using a demo account. Limited functionality available."
                        if is_demo
                        else f"Welcome back, {username}!"
                    )
                    flash(message, "info")

                    # Get next URL from query parameter or default to dashboard
                    next_url = request.args.get("next")
                    if (
                        next_url
                        and next_url.startswith("/")
                        and not next_url.startswith("//")
                    ):
                        return redirect(next_url)
                    return redirect(url_for("index"))
                else:
                    flash("Failed to create user session.", "error")
            else:
                flash("Failed to create or update user.", "error")

    return render_template("login.html")


@app.route("/login-hiveauth", methods=["POST"])
def login_hiveauth():
    """Handle HiveAuth login submission"""
    username = request.form.get("username")
    auth_token = request.form.get("auth_token")
    uuid = request.form.get("uuid")

    if not all([username, auth_token, uuid]):
        flash("Missing authentication details. Please try again.", "danger")
        return redirect(url_for("login"))

    # Verify HiveAuth credentials (implement verify_hiveauth in utils/hiveauth.py)
    from utils.hiveauth import verify_hiveauth

    verification = verify_hiveauth(username, auth_token, uuid)
    if not verification.get("success"):
        flash(
            "Authentication failed. Please try again or use another login method.",
            "danger",
        )
        return redirect(url_for("login"))

    # For this demo, create or update the user in the database
    user_id = db.create_or_update_user(username, "hiveauth")
    if user_id:
        session["username"] = username
        flash("Login successful.", "success")
        return redirect(url_for("index"))
    else:
        flash("User login failed. Please try again.", "danger")
        return redirect(url_for("login"))


@app.route("/api/check-hiveauth", methods=["GET"])
def check_hiveauth():
    """API endpoint to check HiveAuth status"""
    username = request.args.get("username")
    token = request.args.get("auth_token") or request.args.get("token")
    uuid = request.args.get("uuid")

    if not all([username, token, uuid]):
        return jsonify({"error": "Missing required parameters"}), 400

    # In a real app, you would check with the HiveAuth service
    # For demo purposes, we'll simulate authentication success
    return jsonify({"authenticated": True, "username": username})


@app.route("/logout")
def logout():
    """Logout route"""
    if "username" in session:
        # Log the logout action
        db.log_user_activity(session["username"], "auth", {"action": "logout"})

        # Delete the session if we have a session_id
        if "session_id" in session:
            session_manager.delete_session(session["session_id"])

    # Clear the Flask session
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/posts")
def posts():
    """Posts page with combined trending and filtered views"""
    # If user is logged in, log this activity
    if "username" in session:
        db.log_user_activity(session["username"], "page_view", {"page": "posts"})

    # Get the feed type from query parameters (default to trending)
    feed_type = request.args.get("feed", "trending")
    tag = request.args.get("tag")

    # Check if server is still initializing the feed
    is_initializing = not posts_cache.is_feed_ready(feed_type)

    # Improve AJAX response for feed status during initialization
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify(
            {
                "initializing": is_initializing,
                "message": f"Loading {feed_type} posts...",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "no_refresh": True,
            }
        )

    # Always set no_auto_refresh to True for the posts page
    no_auto_refresh = True

    # Fetch posts from cache with non-blocking approach
    try:
        # Use a short timeout to get posts - prevents long blocking operations
        start_time = time.time()
        posts_data = posts_cache.get_posts(
            feed_type=feed_type,
            tag=tag,
            limit=50,
            timeout=0.5,  # Limit initial load to 50
        )
        logger.debug(f"Posts fetch took {time.time() - start_time:.3f}s")

        # If no posts were returned or an empty list, use demo data
        if not posts_data:
            posts_data = DEMO_POSTS.copy()
            # Add a flag to indicate these are demo posts
            for post in posts_data:
                post["is_demo"] = True
        else:
            # Mark posts as not being demo posts
            for post in posts_data:
                post["is_demo"] = False
    except Exception as e:
        logger.error(f"Failed to fetch posts from cache: {e}")
        # Fallback to demo data if cache lookup fails
        posts_data = DEMO_POSTS.copy()
        # Add a flag to indicate these are demo posts
        for post in posts_data:
            post["is_demo"] = True

    # Check if the user is logged in
    is_logged_in = "username" in session
    username = session.get("username")

    # Add a meta tag to indicate if this is the first load or a refreshed load
    is_cache_fresh = posts_cache.is_cache_fresh(feed_type, tag)

    # Check if cache initialization is complete
    cache_initializing = not posts_cache._startup_complete or is_initializing

    return render_template(
        "posts.html",
        posts=posts_data,
        feed_type=feed_type,
        tag=tag,
        is_logged_in=is_logged_in,
        username=username,
        is_cache_fresh=is_cache_fresh,
        cache_refreshing=cache_initializing,
        is_feed_initializing=is_initializing,
        no_auto_refresh=no_auto_refresh,
    )


# Redirect from /trending to /posts to maintain backward compatibility
@app.route("/trending")
def trending():
    """Redirect trending to posts with trending filter"""
    return redirect(url_for("posts", feed="trending"))


@app.route("/post/<author>/<permlink>")
def view_post(author, permlink):
    """View a specific post"""
    # Check if post is cached in database
    cached_post = db.get_cached_post(author, permlink)

    if cached_post:
        post = cached_post
    else:
        # Fetch post from Hive blockchain
        try:
            hive_api_client = get_hive_api()
            post = hive_api_client.get_post(author, permlink)

            # If post is found in blockchain, cache it for future use
            if post:
                db.cache_post(author, permlink, post)
        except Exception as e:
            logger.error(f"Failed to fetch post from blockchain: {e}")
            post = None

            # Fallback to demo posts if API fails
            for p in DEMO_POSTS:
                if p["author"] == author and p["permlink"] == permlink:
                    post = p
                    break

    if not post:
        flash("Post not found.", "error")
        return redirect(url_for("posts"))

    # If user is logged in, log this activity
    if "username" in session:
        db.log_user_activity(
            session["username"],
            "post_view",
            {"author": author, "permlink": permlink, "title": post.get("title")},
        )

    # Fetch comments for this post (if any)
    comments = []
    try:
        if post.get("comment_count", 0) > 0:
            hive_api_client = get_hive_api()
            comments = hive_api_client.get_comments(author, permlink)
    except Exception as e:
        logger.error(f"Failed to fetch comments for post {author}/{permlink}: {e}")
        # Continue without comments

    return render_template("post_detail.html", post=post, comments=comments)


@app.route("/post/<author>/<permlink>/comment", methods=["POST"])
@login_required
def add_comment(author, permlink):
    """Add a comment to a post"""
    if not request.form.get("comment_body"):
        flash("Comment text is required.", "warning")
        return redirect(url_for("view_post", author=author, permlink=permlink))

    comment_body = request.form.get("comment_body")
    parent_author = author
    parent_permlink = permlink
    comment_author = session.get("username")

    # Get HiveSigner token if available (for authenticated operations)
    hivesigner_token = session.get("hivesigner_token")

    try:
        # For demo accounts or if demo comment checkbox is checked, create a fake comment
        if session.get("auth_method") == "demo" or request.form.get("demo_comment"):
            # Generate a unique timestamp-based permlink for the comment
            timestamp = int(time.time())
            comment_permlink = f"re-{permlink[:8]}-{timestamp}"

            # Create a simulated comment
            comment = {
                "id": f"@{comment_author}/{comment_permlink}",
                "author": comment_author,
                "permlink": comment_permlink,
                "parent_author": parent_author,
                "parent_permlink": parent_permlink,
                "body": comment_body,
                "created": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "depth": 1,
                "children": 0,
                "net_votes": 0,
                "is_demo": True,
            }

            # Save the comment to database for demo purposes
            db.cache_comment(comment)

            flash(
                "Demo comment added successfully. Note: This comment only exists locally and was not published to the blockchain.",
                "info",
            )
        else:
            # Get Hive API client for real blockchain operations
            hive_api_client = get_hive_api()

            # Try to create the comment using blockchain
            success, result = hive_api_client.broadcast_transaction(
                "create_comment",
                {
                    "parent_author": parent_author,
                    "parent_permlink": parent_permlink,
                    "author": comment_author,
                    "body": comment_body,
                    "hivesigner_token": hivesigner_token,
                },
            )

            if success:
                flash(
                    "Your comment has been published to the Hive blockchain!", "success"
                )
            else:
                error_msg = result.get("error", "Unknown error occurred")
                flash(f"Failed to publish comment: {error_msg}", "error")

    except Exception as e:
        logger.exception(f"Error adding comment: {e}")
        flash(f"An error occurred: {str(e)}", "error")

    # Redirect back to the post
    return redirect(url_for("view_post", author=author, permlink=permlink))


@app.route("/profile/<username>")
def profile(username):
    """User profile page"""
    # Check if user exists in database
    user_data = db.get_user(username)

    if not user_data and username != "demo":
        flash("User not found.", "error")
        return redirect(url_for("index"))

    # If viewing own profile, log the activity
    if "username" in session and session["username"] == username:
        db.log_user_activity(
            session["username"], "profile_view", {"username": username}
        )

    # For demo, use static data
    # For real accounts, fetch from Hive API
    if username == "demo":
        posts = DEMO_POSTS
    else:
        # Get real user posts from Hive blockchain
        try:
            hive_api_client = get_hive_api()
            posts = hive_api_client.get_user_posts(username, limit=10)
        except Exception as e:
            logger.error(f"Error fetching posts for {username}: {e}")
            posts = []  # Fallback to empty list if API call fails

    # Use profile data from database if available
    profile_details = {}
    if user_data:
        # Initialize profile to empty dict if it's None to avoid AttributeError
        profile = user_data.get("profile") or {}

        # Fetch user profile from blockchain for non-demo users
        blockchain_profile = None
        if username != "demo":
            try:
                hive_api_client = get_hive_api()
                blockchain_profile = hive_api_client.get_user_profile(username)
                # Ensure blockchain_profile is not None to avoid AttributeError
                blockchain_profile = blockchain_profile or {}
            except Exception as e:
                logger.error(f"Error fetching blockchain profile for {username}: {e}")
                blockchain_profile = {}  # Ensure it's an empty dict on error

        if blockchain_profile:
            # Use blockchain data for profile details
            profile_details = {
                "username": username,
                "name": blockchain_profile.get("name", username),
                "about": blockchain_profile.get("about", "No bio yet"),
                "location": blockchain_profile.get("location", ""),
                "website": blockchain_profile.get("website", ""),
                "followers": blockchain_profile.get("followers", 0),
                "following": blockchain_profile.get("following", 0),
                "post_count": blockchain_profile.get("post_count", len(posts)),
                "reputation": blockchain_profile.get("reputation", "0"),
                "join_date": blockchain_profile.get(
                    "join_date", user_data.get("created_at", "2023-01-01")
                ),
                "profile_image": blockchain_profile.get(
                    "profile_image", f"https://images.hive.blog/u/{username}/avatar"
                ),
                "cover_image": blockchain_profile.get("cover_image", ""),
            }
        else:
            # Fall back to database profile with placeholder stats
            profile_details = {
                "username": username,
                "name": profile.get("name", username),
                "about": profile.get("about", "No bio yet"),
                "location": profile.get("location", ""),
                "website": profile.get("website", ""),
                "followers": 0,  # Placeholder
                "following": 0,  # Placeholder
                "post_count": len(posts),
                "reputation": "0",  # Placeholder
                "join_date": user_data.get("created_at", "2023-01-01"),
                "profile_image": profile.get(
                    "profile_image", f"https://images.hive.blog/u/{username}/avatar"
                ),
                "cover_image": profile.get("cover_image", ""),
            }
    else:
        # Default data for demo user
        profile_details = {
            "username": username,
            "name": "Demo User",
            "about": "This is a demo account for testing HiveBuzz features.",
            "location": "Blockchain",
            "website": "https://hive.blog",
            "followers": 256,
            "following": 128,
            "post_count": len(posts),
            "reputation": "72",
            "join_date": "2023-01-01",
            "profile_image": f"https://images.hive.blog/u/{username}/avatar",
            "cover_image": "",
        }

    return render_template(
        "profile.html", profile_user=username, user_data=profile_details, posts=posts
    )


@app.route("/create", methods=["GET", "POST"])
@login_required
def create_post():
    """Create post page with Hive blockchain posting capability"""
    if request.method == "POST":
        # Get form data
        title = request.form.get("title")
        body = request.form.get("body")
        tags_str = request.form.get("tags")

        if not title or not body:
            flash("Title and content are required", "warning")
            return redirect(url_for("create_post"))

        # Parse tags from comma-separated string
        tags = (
            [tag.strip() for tag in tags_str.split(",") if tag.strip()]
            if tags_str
            else []
        )

        # Make sure first tag exists
        if not tags:
            tags = ["hivebuzz"]  # Default tag if none provided

        # Get current username
        username = session.get("username")

        # Get HiveSigner token if available
        hivesigner_token = session.get("hivesigner_token")

        try:
            # Get Hive API client
            hive_api_client = get_hive_api()

            # Check if we have what we need to post
            if not username:
                flash("You must be logged in to create a post", "error")
                return redirect(url_for("login"))

            # Try to create the post using broadcast_transaction
            success, result = hive_api_client.broadcast_transaction(
                "create_post",
                {
                    "author": username,
                    "title": title,
                    "body": body,
                    "tags": tags,
                    "hivesigner_token": hivesigner_token,
                },
            )

            if success:
                # Log activity
                db.log_user_activity(
                    username,
                    "post_create",
                    {
                        "title": title,
                        "tags": tags,
                        "permlink": result.get("permlink"),
                        "success": True,
                    },
                )
                flash("Your post has been published to the Hive blockchain!", "success")
                return redirect(
                    url_for(
                        "view_post", author=username, permlink=result.get("permlink")
                    )
                )
            else:
                # Log the failed attempt
                db.log_user_activity(
                    username,
                    "post_create",
                    {
                        "title": title,
                        "tags": tags,
                        "success": False,
                        "error": result.get("error", "Unknown error"),
                    },
                )

                error_msg = result.get("error", "Unknown error occurred")
                flash(f"Failed to publish post: {error_msg}", "error")
                return render_template(
                    "create_post.html", title=title, body=body, tags=tags_str
                )

        except Exception as e:
            logger.exception(f"Error creating post: {e}")
            flash(f"An error occurred: {str(e)}", "error")
            return render_template(
                "create_post.html", title=title, body=body, tags=tags_str
            )

    # Log page view
    db.log_user_activity(session["username"], "page_view", {"page": "create_post"})

    return render_template("create_post.html")


@app.route("/create/demo", methods=["POST"])
@login_required
def create_demo_post():
    """Create a demo post without broadcasting to the blockchain"""
    # Get form data
    title = request.form.get("title")
    body = request.form.get("body")
    tags_str = request.form.get("tags")

    if not title or not body:
        flash("Title and content are required", "warning")
        return redirect(url_for("create_post"))

    # Parse tags from comma-separated string
    tags = (
        [tag.strip() for tag in tags_str.split(",") if tag.strip()]
        if tags_str
        else ["hivebuzz"]
    )

    # Get current username
    username = session.get("username")

    # Generate a unique permlink
    # Create a slug from the title
    slug = slugify_function(title)
    if not slug:
        slug = "untitled"

    # Add timestamp to make it unique
    permlink = f"{slug}-{int(time.time())}"

    # Simulate a blockchain post by creating a cached version in the database
    post_data = {
        "id": f"@{username}/{permlink}",
        "author": username,
        "permlink": permlink,
        "title": title,
        "body": body,
        "created": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "category": tags[0] if tags else "hivebuzz",
        "tags": tags,
        "vote_count": 0,
        "comment_count": 0,
        "payout": "0.000 HBD",
        "image": None,  # Extract first image from body if needed
    }

    # Cache the post in the database
    db.cache_post(username, permlink, post_data)

    # Log activity
    db.log_user_activity(
        username,
        "post_create",
        {
            "title": title,
            "tags": tags,
            "permlink": permlink,
            "success": True,
            "demo": True,
        },
    )

    flash(
        "Your demo post has been created! Note: This post only exists in the HiveBuzz app and was not published to the Hive blockchain.",
        "info",
    )
    return redirect(url_for("view_post", author=username, permlink=permlink))


@app.route("/api/get_account_info/<username>")
def get_account_info(username):
    """API to get account information"""
    # Check if user exists in database
    user_data = db.get_user(username)

    if user_data:
        profile = user_data.get("profile", {})

        # Return user information
        return jsonify(
            {
                "username": username,
                "name": profile.get("name", username),
                "about": profile.get("about", ""),
                "profile_image": profile.get(
                    "profile_image", f"https://images.hive.blog/u/{username}/avatar"
                ),
                "is_demo": bool(user_data.get("is_demo", False)),
            }
        )
    else:
        # User not found
        return jsonify({"error": "User not found"}), 404


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """User settings page"""
    if request.method == "POST":
        # Handle settings update
        theme_color = request.form.get("theme_color")
        dark_mode = request.form.get("dark_mode") == "on"
        display_nsfw = request.form.get("display_nsfw") == "on"
        language = request.form.get("language")

        # Get custom color if theme is set to custom
        custom_color = None
        if theme_color == "custom":
            custom_color = request.form.get("custom_color")

            # Generate lighter and darker variants for the custom color
            if custom_color:
                try:
                    # Convert hex to RGB
                    r = int(custom_color[1:3], 16)
                    g = int(custom_color[3:5], 16)
                    b = int(custom_color[5:7], 16)

                    # Generate lighter variant (20% lighter)
                    lighter_r = min(255, int(r + (255 - r) * 0.2))
                    lighter_g = min(255, int(g + (255 - g) * 0.2))
                    lighter_b = min(255, int(b + (255 - b) * 0.2))
                    custom_color_light = (
                        f"#{lighter_r:02x}{lighter_g:02x}{lighter_b:02x}"
                    )

                    # Generate darker variant (20% darker)
                    darker_r = max(0, int(r * 0.8))
                    darker_g = max(0, int(g * 0.8))
                    darker_b = max(0, int(b * 0.8))
                    custom_color_dark = f"#{darker_r:02x}{darker_g:02x}{darker_b:02x}"
                except Exception as e:
                    logger.error(f"Error processing custom color: {e}")
                    custom_color_light = "#9589f6"  # Default light variant
                    custom_color_dark = "#4824eb"  # Default dark variant
            else:
                custom_color = "#7367f0"  # Default custom color
                custom_color_light = "#9589f6"  # Default light variant
                custom_color_dark = "#4824eb"  # Default dark variant

        # Update preferences in database
        preferences = {
            "theme_color": theme_color,
            "dark_mode": 1 if dark_mode else 0,  # SQLite uses integers for booleans
            "display_nsfw": 1 if display_nsfw else 0,
            "language": language,
        }

        if custom_color:
            preferences["custom_color"] = custom_color
            preferences["custom_color_light"] = custom_color_light
            preferences["custom_color_dark"] = custom_color_dark

        if db.save_user_preferences(session["username"], preferences):
            # Update session for immediate effect
            session["dark_mode"] = dark_mode
            session["theme_color"] = theme_color
            if custom_color:
                session["custom_color"] = custom_color
                session["custom_color_light"] = custom_color_light
                session["custom_color_dark"] = custom_color_dark

            flash("Settings updated successfully!", "success")
        else:
            flash("Failed to save settings.", "error")

        return redirect(url_for("settings"))

    # Get current user preferences
    user_data = db.get_user(session["username"]) or {}

    # Create preferences dictionary to pass to the template
    preferences = {
        "theme_color": user_data.get("theme_color", "blue"),
        "dark_mode": bool(user_data.get("dark_mode", False)),
        "display_nsfw": bool(user_data.get("display_nsfw", False)),
        "language": user_data.get("language", "en"),
        "custom_color": user_data.get("custom_color", "#7367f0"),
        "custom_color_light": user_data.get("custom_color_light", "#9589f6"),
        "custom_color_dark": user_data.get("custom_color_dark", "#4824eb"),
        # Add other preference fields if needed by the template
        "notify_comments": bool(user_data.get("notify_comments", False)),
        "notify_upvotes": bool(user_data.get("notify_upvotes", False)),
        "notify_follows": bool(user_data.get("notify_follows", False)),
        "show_voting_value": bool(user_data.get("show_voting_value", True)),
        "show_profile": bool(user_data.get("show_profile", True)),
    }

    return render_template(
        "settings.html",
        user=user_data,
        preferences=preferences,
    )


@app.route("/wallet")
@login_required
def wallet():
    """User wallet page with real blockchain data"""
    username = session["username"]
    is_demo = session.get("auth_method") == "demo"

    # Log this activity
    db.log_user_activity(username, "page_view", {"page": "wallet"})

    try:
        # Get Hive API client
        hive_api_client = get_hive_api()

        # Fetch wallet data and transaction history
        if is_demo:
            wallet_data = hive_api_client._get_mock_wallet(username)
            transactions = hive_api_client._get_mock_account_history(username, limit=20)
        else:
            wallet_data = hive_api_client.get_user_wallet(username)
            transactions = hive_api_client.get_account_history(username, limit=20)

        # Add market data (in production, fetch from market API)
        market_data = {
            "hive_usd": 0.336,
            "hbd_usd": 0.994,
            "savings_apr": 20.0,
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        }

        return render_template(
            "wallet.html",
            wallet=wallet_data,
            transactions=transactions,
            market=market_data,
            is_demo=is_demo,  # Pass is_demo to the template
        )
    except Exception as e:
        # Log the error
        logger.exception(f"Error loading wallet for {username}: {e}")

        # Show an error message
        flash("Unable to load wallet data. Please try again later.", "error")

        # Return wallet with mock data as fallback
        return render_template(
            "wallet.html",
            wallet=(
                hive_api_client._get_mock_wallet(username)
                if "hive_api_client" in locals()
                else {}
            ),
            transactions=[],
            market={
                "hive_usd": 0.00,
                "hbd_usd": 0.00,
                "savings_apr": 0.0,
                "last_updated": "Data unavailable",
            },
            error=True,
            is_demo=is_demo,  # Pass is_demo to the template
        )


@app.route("/hivesigner/callback")
def hivesigner_callback():
    """HiveSigner callback endpoint"""
    # Get the authorization code from the query parameters
    code = request.args.get("code")
    state = request.args.get("state", "")

    if not code:
        flash("Authorization failed - no code provided", "error")
        return redirect(url_for("login"))

    # Get callback URL for token exchange
    redirect_uri = url_for("hivesigner_callback", _external=True)

    # Log the callback parameters for debugging
    logger.info(
        f"HiveSigner callback received: code={code[:10]}..., state={state}, redirect_uri={redirect_uri}"
    )

    # Get HiveSigner client
    hivesigner = get_hivesigner_client()
    if not hivesigner:
        flash("HiveSigner client not initialized", "error")
        return redirect(url_for("login"))

    # Exchange code for token
    success, result = hivesigner.get_token(code, redirect_uri)

    if not success:
        error_message = result.get("error", "Unknown error")
        details = result.get("details", "No additional details")
        logger.error(f"HiveSigner authentication failed: {error_message} - {details}")
        # Provide a more user-friendly error message
        flash(
            "Authentication failed. Please try again or use another login method.",
            "error",
        )
        return redirect(url_for("login"))

    # Implement fallback option for unusual response formats
    if isinstance(result, dict) and "access_token" not in result:
        if "username" in result:
            # Direct user info without token - unusual but we can work with it
            username = result["username"]
            access_token = "direct_user_info"  # Placeholder
        else:
            # No recognizable data - fail gracefully
            logger.error(f"Unexpected HiveSigner response format: {result}")
            flash(
                "Received unexpected response from HiveSigner. Please try again.",
                "error",
            )
            return redirect(url_for("login"))
    else:
        # Get access token from regular response
        access_token = result.get("access_token")

    if not access_token:
        logger.error(f"No access token found in response: {result}")
        flash("Invalid authentication response", "error")
        return redirect(url_for("login"))

    # Verify token and get user info
    try:
        success, user_data = hivesigner.verify_token(access_token)
        if not success or "user" not in user_data:
            logger.error(
                f"Failed to verify token: {user_data.get('error', 'Unknown error')}"
            )
            flash("Failed to verify authentication", "error")
            return redirect(url_for("login"))

        username = user_data["user"]
    except Exception:
        logger.exception("Exception during token verification")
        flash("An error occurred during authentication verification", "error")
        return redirect(url_for("login"))

    if not username:
        flash("No username returned from HiveSigner", "error")
        return redirect(url_for("login"))

    # Create or update user in database
    try:
        user_id = db.create_or_update_user(username, "hivesigner")
        if not user_id:
            logger.error(f"Failed to create user in database: {username}")
            flash("Failed to create user account. Please try again.", "error")
            return redirect(url_for("login"))

        # Create a new session
        session_data = session_manager.create_session(
            username=username,
            auth_method="hivesigner",
            additional_data={
                "code": code,
                "state": state,
                "access_token": access_token,
            },
        )

        if not session_data:
            logger.error(f"Failed to create session for user: {username}")
            flash("Failed to create user session.", "error")
            return redirect(url_for("login"))

        # Set session data
        session["username"] = username
        session["auth_method"] = "hivesigner"
        session["session_id"] = session_data["session_id"]
        session["hivesigner_token"] = access_token

        # Load user preferences
        user_data = db.get_user(username)
        if user_data:
            if user_data.get("dark_mode") is not None:
                session["dark_mode"] = bool(user_data.get("dark_mode"))
            if user_data.get("theme_color"):
                session["theme_color"] = user_data.get("theme_color")
            if (
                user_data.get("custom_color")
                and user_data.get("theme_color") == "custom"
            ):
                session["custom_color"] = user_data.get("custom_color")
                session["custom_color_light"] = user_data.get("custom_color_light")
                session["custom_color_dark"] = user_data.get("custom_color_dark")

        # Log activity
        db.log_user_activity(
            username, "auth", {"action": "login", "method": "hivesigner"}
        )

        flash("Successfully logged in with HiveSigner!", "success")
        return redirect(url_for("index"))

    except Exception as e:
        logger.exception(f"Unexpected error during HiveSigner login process: {e}")
        flash("An unexpected error occurred. Please try again.", "error")
        return redirect(url_for("login"))


@app.route("/transactions")
@login_required
def transactions():
    """Transactions page to view and manage blockchain transactions"""
    username = session.get("username")
    # Log this activity
    db.log_user_activity(username, "page_view", {"page": "transactions"})

    # Ensure username is not None for type safety
    assert username is not None, "username is None; user must be logged in."

    try:
        # Get Hive API client
        hive_api_client = get_hive_api()

        # Get user wallet data and transaction history
        user_history = hive_api_client.get_account_history(username, limit=50)

        # Get some recent blockchain transactions
        # This would show public network activity
        recent_transactions = hive_api_client.get_recent_transactions(limit=10)

        return render_template(
            "transactions.html",
            user_history=user_history,
            recent_transactions=recent_transactions,
            username=username,
        )
    except Exception as e:
        # Log the error
        logger.exception(f"Error loading transactions for {username}: {e}")

        # Show an error message
        flash("Unable to load transaction data. Please try again later.", "error")

        # Return transactions page with empty data as fallback
        return render_template(
            "transactions.html",
            user_history=[],
            recent_transactions=[],
            username=username,
            error=True,
        )


@app.route("/api/transaction/<tx_id>")
@login_required
def get_transaction(tx_id):
    """API endpoint to get details of a specific transaction"""
    if not tx_id:
        return jsonify({"success": False, "error": "Transaction ID required"}), 400

    try:
        # Get Hive API client
        hive_api_client = get_hive_api()

        # Get transaction
        transaction = hive_api_client.get_transaction(tx_id)

        if transaction:
            return jsonify({"success": True, "transaction": transaction})
        else:
            return jsonify({"success": False, "error": "Transaction not found"}), 404
    except Exception as e:
        logger.exception(f"Error getting transaction {tx_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/broadcast", methods=["POST"])
@login_required
def broadcast_transaction():
    """API endpoint to broadcast a transaction to the blockchain"""
    if not request.is_json:
        return jsonify({"success": False, "error": "JSON required"}), 400

    data = request.get_json()
    operation_name = data.get("operation")
    operation_data = data.get("data")

    if not operation_name or not operation_data:
        return (
            jsonify({"success": False, "error": "Operation name and data required"}),
            400,
        )

    try:
        # Get Hive API client
        hive_api_client = get_hive_api()

        # Broadcast the transaction
        success, result = hive_api_client.broadcast_transaction(
            operation_name, operation_data
        )

        if success:
            # Log the transaction
            db.log_user_activity(
                session["username"],
                "transaction",
                {"operation": operation_name, "tx_id": result.get("transaction_id")},
            )

            return jsonify({"success": True, "result": result})
        else:
            return (
                jsonify(
                    {"success": False, "error": result.get("error", "Unknown error")}
                ),
                400,
            )
    except Exception as e:
        logger.exception(f"Error broadcasting transaction: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# Update Flask app initialization to include blueprint for static files
static_bp = Blueprint(
    "static", __name__, static_folder="static", static_url_path="/static"
)
app.register_blueprint(static_bp)


# Add a context processor to inject information about current page to templates
@app.context_processor
def inject_template_vars():
    return {
        "page": request.endpoint,
        "path": request.path,
        "dark_mode": session.get("dark_mode", False),
        "theme_color": session.get("theme_color", "blue"),
    }


# Add context processor to make configuration available to templates
@app.context_processor
def inject_config():
    """Make selected configuration variables available to templates"""
    return {
        "config": {
            "HIVESIGNER_APP_NAME": app.config["HIVESIGNER_APP_NAME"],
            "HIVESIGNER_REDIRECT_URI": app.config["HIVESIGNER_REDIRECT_URI"],
            "HIVESIGNER_APP_HOST": app.config["HIVESIGNER_APP_HOST"],
            "APP_URL": app.config["APP_URL"],
            "DEBUG": app.config["DEBUG"],
        }
    }


@app.context_processor
def inject_now():
    """Inject current UTC time into templates using timezone-aware datetime"""
    return {"now": datetime.now(timezone.utc)}


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(e):
    logger.error(f"Internal server error: {e}")
    return render_template("error.html", error=str(e)), 500


@app.route("/maintenance/clear-expired-sessions")
def clear_expired_sessions():
    """Maintenance endpoint to clear expired sessions"""
    # This should be protected in production
    if request.remote_addr != "127.0.0.1" and not app.debug:
        return jsonify({"error": "Unauthorized"}), 403

    count = session_manager.clear_expired_sessions()
    return jsonify({"success": True, "cleared_count": count}), 200


@app.route("/dashboard")
def dashboard():
    """Dashboard redirect - ensures proper navigation"""
    if "username" in session:
        return redirect(url_for("index"))
    else:
        flash("Please log in to access your dashboard", "warning")
        return redirect(url_for("login"))


# Add a route to check API initialization status for diagnostics
@app.route("/api/status")
def api_status():
    """API endpoint to check API and cache initialization status"""
    try:
        hive_api_client = get_hive_api()

        # Get detailed cache status
        cache_status = posts_cache.get_cache_status()

        # Add a timestamp to prevent browser caching
        current_time = datetime.now(timezone.utc).isoformat()

        # Check if this request should not trigger a page reload
        no_reload = request.headers.get("X-No-Refresh") == "true"

        return jsonify(
            {
                "initialized": hive_api_client.initialized,
                "initializing": hive_api_client.initializing,
                "hive_available": _beem_available,
                "beem_initialized": hive_api_client.hive is not None,
                "direct_api_available": True,
                "cache": cache_status,
                "cache_initialized": posts_cache._startup_complete,
                "priority_feeds_loaded": posts_cache.initialized,
                "timestamp": current_time,  # Add timestamp to prevent caching
                "no_reload": no_reload,  # Flag to prevent reload
            }
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "error": str(e),
                    "initialized": False,
                    "cache_initialized": False,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "no_reload": True,
                }
            ),
            500,
        )


@app.route("/api/posts")
def api_posts():
    """API endpoint for loading more posts via AJAX"""
    feed_type = request.args.get("feed", "trending")
    tag = request.args.get("tag")
    page = int(request.args.get("page", 1))
    limit = int(
        request.args.get("limit", 20)
    )  # Default to 20 posts per page, but allow custom limits

    try:
        # For page 1, use the cache
        if page == 1:
            posts_data = posts_cache.get_posts(
                feed_type=feed_type, tag=tag, limit=limit
            )
        else:
            # For additional pages, we'd need to fetch from the API
            # This is a simplified version - ideally we'd cache multiple pages
            hive_api_client = get_initialized_api()

            if feed_type == "trending":
                posts_data = hive_api_client.get_trending_posts(limit=limit, tag=tag)
            elif feed_type == "created" or feed_type == "new":
                posts_data = hive_api_client.get_trending_posts(limit=limit, tag=tag)
                posts_data.sort(key=lambda post: post.get("created", ""), reverse=True)
            elif feed_type == "hot":
                posts_data = hive_api_client.get_trending_posts(limit=limit, tag=tag)
            elif feed_type == "promoted":
                posts_data = hive_api_client.get_trending_posts(limit=limit, tag=tag)
            else:
                posts_data = hive_api_client.get_trending_posts(limit=limit, tag=tag)

        # Make sure all posts have an ID
        for i, post in enumerate(posts_data):
            if "id" not in post or not post["id"]:
                # Create a unique ID based on author and permlink
                if "author" in post and "permlink" in post:
                    post["id"] = f"{post['author']}-{post['permlink']}"
                else:
                    # Fallback to a position-based ID
                    post["id"] = f"post-{int(time.time())}-{i}"

        # Return the posts with a hasMore flag that indicates if there are likely more posts to load
        return jsonify(
            {
                "posts": posts_data,
                "hasMore": len(posts_data) >= limit,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"API error fetching posts: {e}")
        return jsonify({"error": str(e), "posts": [], "hasMore": False})


@app.route("/api/check-feed-status")
def check_feed_status():
    """Check if a specific feed is ready"""
    feed_type = request.args.get("feed", "trending")
    tag = request.args.get("tag")

    try:
        is_ready = posts_cache.is_feed_ready(feed_type)
        has_posts = (
            len(posts_cache.get_posts(feed_type=feed_type, tag=tag, limit=1)) > 0
        )

        return jsonify(
            {
                "ready": is_ready and has_posts,
                "has_posts": has_posts,
                "updating": posts_cache.is_feed_initializing(feed_type),
                "startup_complete": posts_cache._startup_complete,
            }
        )
    except Exception as e:
        logger.error(f"Error checking feed status: {e}")
        return jsonify({"ready": False, "error": str(e)})


# Add a cleanup endpoint for maintenance
@app.route("/maintenance/clear-cache")
def clear_cache():
    """Maintenance endpoint to clear various caches"""
    # This should be protected in production
    if request.remote_addr != "127.0.0.1" and not app.debug:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        # Parse parameters
        older_than = int(request.args.get("older_than", "3600"))  # Default 1 hour
        type = request.args.get("type", "all")

        result = {"success": True, "cleared": {}}

        # Clear session cache if requested
        if type in ["all", "sessions"]:
            sessions_count = session_manager.clear_expired_sessions()
            result["cleared"]["sessions"] = sessions_count

        # Clear posts cache if requested
        if type in ["all", "posts"]:
            posts_count = posts_cache.clear_cache_files(older_than=older_than)
            result["cleared"]["posts"] = posts_count

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return jsonify({"error": str(e)}), 500


# Ensure clean shutdown
def cleanup_on_exit():
    """Clean up resources on application exit"""
    logger.info("Shutting down application...")

    # Stop the posts cache refresh thread first
    if "posts_cache" in globals():
        logger.info("Stopping posts cache refresh thread...")

        # First save all caches to disk
        logger.info("Saving all post caches to disk...")
        posts_cache.save_all_caches()

        # Then stop the thread
        posts_cache.stop()

    logger.info("Application shutdown complete")

# Make sure the cleanup function is registered
atexit.register(cleanup_on_exit)

@app.template_filter("markdown")
def render_markdown(text):
    """Convert markdown text to safe HTML"""
    if not text:
        return ""
    # Convert markdown to HTML
    html = markdown.markdown(
        text,
        extensions=[
            "markdown.extensions.fenced_code",
            "markdown.extensions.tables",
            "markdown.extensions.nl2br",
        ],
    )

    # Clean the HTML to remove potentially harmful tags/attributes
    allowed_tags = [
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
        "br",
        "a",
        "abbr",
        "acronym",
        "b",
        "blockquote",
        "code",
        "em",
        "i",
        "li",
        "ol",
        "strong",
        "ul",
        "pre",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "img",
        "span",
        "div",
        "strike",
        "del",
    ]
    allowed_attrs = {
        "a": ["href", "title", "rel"],
        "img": ["src", "alt", "title", "width", "height"],
        "*": ["class"],
    }

    clean_html = bleach.clean(
        html, tags=allowed_tags, attributes=allowed_attrs, strip=True
    )

    return Markup(clean_html)


@app.route("/api/posts/stream")
def stream_posts():
    """Stream new posts to the client using Server-Sent Events"""

    def event_stream():
        try:
            # Simulate new posts being added over time
            while True:
                # Fetch the latest posts (e.g., from a database or API)
                new_posts = get_new_posts()  # Replace with your actual function

                if new_posts:
                    # Yield the new posts as a JSON object
                    yield f"data: {json.dumps({'posts': new_posts})}\n\n"

                time.sleep(5)  # Adjust the interval as needed

        except GeneratorExit:
            logger.info("Client disconnected from event stream")

    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")


def get_new_posts():
    """Dummy function to simulate fetching new posts"""
    # Replace this with your actual logic to fetch new posts from the Hive blockchain
    # or your data source
    time.sleep(2)  # Simulate network delay
    return [
        {
            "id": 4,
            "author": "newuser",
            "permlink": "new-post",
            "title": "A New Post",
            "body": "This is a new post added dynamically.",
            "created": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "payout": "5.00",
            "tags": ["hivebuzz", "new"],
            "vote_count": 10,
            "comment_count": 2,
        }
    ]


@app.route("/api/posts/new")
def get_new_posts_api():
    """API endpoint to get new posts"""
    feed_type = request.args.get("feed", "trending")
    tag = request.args.get("tag")
    after = request.args.get("after", "")  # Get post ID to fetch posts after this one
    new_only = (
        request.args.get("new_only") == "true"
    )  # Whether to return only new posts

    try:
        # Get posts from cache based on the request type
        if new_only:
            new_posts = posts_cache.get_posts(
                feed_type=feed_type, tag=tag, limit=25, new_only=True
            )
        else:
            # Get all posts (including new ones)
            new_posts = posts_cache.get_posts(
                feed_type=feed_type, tag=tag, limit=25, include_new=True
            )

        # Make sure posts have IDs - add IDs if missing
        for i, post in enumerate(new_posts):
            if "id" not in post or not post["id"]:
                # Generate a unique ID based on author and permlink if available
                if "author" in post and "permlink" in post:
                    post["id"] = f"{post['author']}-{post['permlink']}"
                else:
                    # Fallback to a random ID
                    post["id"] = f"post-{int(time.time())}-{i}"

        # If we have an 'after' parameter, only return posts newer than that one
        if after and new_posts:
            # Since posts are typically ordered by recency, we can just find
            # the index of the specified post and return everything before it
            try:
                for idx, post in enumerate(new_posts):
                    if post["id"] == after:
                        new_posts = new_posts[:idx]
                        break
            except Exception as e:
                logger.error(f"Error filtering posts by 'after' parameter: {e}")

        # Log count for debugging
        logger.info(f"Returning {len(new_posts)} new posts for {feed_type} feed")

        return jsonify(
            {
                "posts": new_posts,
                "hasMore": len(new_posts) > 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Error fetching new posts: {e}")
        return jsonify(
            {
                "error": str(e),
                "posts": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

# ...existing code...

def get_new_posts_from_blockchain(feed_type, tag):
    """Dummy function to simulate fetching new posts from the Hive blockchain"""
    # Replace this with your actual logic to fetch new posts from the Hive blockchain
    time.sleep(1)  # Simulate network delay
    return [
        {
            "id": 4,
            "author": "newuser",
            "permlink": "new-post",
            "title": "A Newer Post",
            "body": "This is a newer post added dynamically.",
            "created": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "payout": "5.00",
            "tags": ["hivebuzz", "new"],
            "vote_count": 10,
            "comment_count": 2,
        }
    ]


@app.route("/api/posts/check")
def check_new_posts():
    """Check if there are new posts available"""
    feed_type = request.args.get("feed", "trending")
    tag = request.args.get("tag")

    try:
        # Get the number of new posts
        new_count = posts_cache.get_new_post_count(feed_type, tag)

        return jsonify(
            {
                "new_count": new_count,
                "feed_type": feed_type,
                "tag": tag,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Error checking for new posts: {e}")
        return (
            jsonify(
                {
                    "error": str(e),
                    "new_count": 0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
            500,
        )


@app.route("/api/posts/merge", methods=["POST"])
def merge_new_posts():
    """Merge new posts into the main posts list"""
    feed_type = request.args.get("feed", "trending")
    tag = request.args.get("tag")

    try:
        # Merge new posts into the main list
        merged_count = posts_cache.merge_new_posts(feed_type, tag)

        return jsonify(
            {
                "merged_count": merged_count,
                "feed_type": feed_type,
                "tag": tag,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Error merging new posts: {e}")
        return (
            jsonify(
                {
                    "error": str(e),
                    "merged_count": 0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
            500,
        )


@app.after_request
def add_no_refresh_headers(response):
    """Add headers to prevent caching and auto-refresh for specific pages"""
    # Get the current path
    path = request.path

    # Check if this is a no-refresh page
    no_refresh_paths = ["/posts", "/post/"]
    is_no_refresh_page = any(path.startswith(p) for p in no_refresh_paths)

    # Add Cache-Control headers for API endpoints
    if path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

        # For API status check with X-No-Refresh header, add special header
        if path == "/api/status" and request.headers.get("X-No-Refresh") == "true":
            response.headers["X-No-Reload"] = "true"

    # For no-refresh pages
    if is_no_refresh_page:
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["X-No-Reload"] = "true"

    return response


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV") == "development"

    # Get API instance to make it available
    api = get_hive_api()

    # Add waitress server for production use
    if not debug:
        try:
            import logging.handlers

            from waitress import serve

            # Configure a callback to log when server is ready
            class ServerReadyHandler(logging.Handler):
                def emit(self, record):
                    if "task" in record.msg and "running" in record.msg:
                        logger.info(
                            f"✅ HiveBuzz server is ready to accept requests on port {port}"
                        )

            # Add our custom handler to the waitress logger
            waitress_logger = logging.getLogger("waitress")
            waitress_logger.addHandler(ServerReadyHandler())

            # Log that we're starting up
            logger.info(f"Starting HiveBuzz server on port {port}")
            serve(app, host="0.0.0.0", port=port, threads=4)
        except ImportError:
            logger.warning(
                "Waitress not installed, falling back to Flask development server"
            )
            app.run(host="0.0.0.0", port=port, debug=debug)
    else:
        # For development, use the Flask built-in server
        logger.info(f"Starting HiveBuzz development server on port {port}")
        logger.info(
            f"✅✅ HiveBuzz development server will be available at http://127.0.0.1:{port}"
        )
        app.run(host="0.0.0.0", port=port, debug=debug, threaded=True)
