"""
Hive API Client for HiveBuzz
Handles interactions with the Hive blockchain
"""

import json
import logging
import threading
import time
from datetime import datetime
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple

import requests

# cSpell: ignore beem

# Configure logging
logger = logging.getLogger(__name__)

# Global variable to ensure we only attempt to import beem once
_tried_beem_import = False
_beem_available = False

# Import beem conditionally - this avoids hard dependency issues
try:
    from beem import Hive
    from beem.account import Account
    from beem.comment import Comment
    from beem.discussions import Discussions, Query
    from beem.exceptions import (
        AccountDoesNotExistsException,
        ContentDoesNotExistsException,
    )
    from beem.nodelist import NodeList

    _beem_available = True
except ImportError as e:
    logger.warning(f"Could not import beem: {e}. Will use direct API calls instead.")
    _tried_beem_import = True


# Add a decorator for asynchronous initialization
def async_init(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=f, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread

    return wrapper


class HiveAPI:
    """
    Class to handle Hive blockchain API interactions
    """

    def __init__(self, api_url: Optional[str] = None):
        """
        Initialize the Hive API client

        Args:
            api_url: Optional custom API endpoint URL
        """
        self.api_url = api_url or "https://api.hive.blog"
        self.hive = None
        self.initialization_thread = None
        self.initialized = False
        self.initializing = False
        self.initialization_timeout = 30  # seconds

        # Initialize with direct API access first for immediate availability
        logger.info(
            "HiveAPI initialized with direct API access for immediate availability"
        )

        # Only start background initialization if beem is available
        if _beem_available:
            # Don't start initialization in constructor - we'll do it lazily when needed
            logger.info(
                "Beem library available, background initialization will start when needed"
            )
        else:
            logger.info("Beem library not available, using direct API calls only")

    @async_init
    def _async_init_beem(self) -> None:
        """Initialize the beem library with working nodes in a background thread"""
        if self.initializing or self.initialized:
            logger.debug("Initialization already in progress or completed")
            return

        self.initializing = True
        try:
            logger.info("Starting Hive API initialization in background thread...")
            self._init_beem()
            self.initialized = True
            self.initializing = False
            logger.info("Hive API initialization completed in background thread")
        except Exception as e:
            logger.error(f"Error in background initialization of Hive API: {e}")
            self.initializing = False

    def _init_beem(self) -> None:
        """Initialize the beem library with working nodes"""
        global _tried_beem_import, _beem_available

        if _tried_beem_import and not _beem_available:
            logger.warning("Beem import was already attempted and failed")
            return

        try:
            # Get nodes from the NodeList
            nodelist = NodeList()
            nodelist.update_nodes()
            nodes = nodelist.get_hive_nodes()

            if not nodes:
                logger.error("No valid Hive nodes found")
                self.hive = None
                return

            # Pass just the first node (string) instead of a list
            self.hive = Hive(node=nodes[0])

            if self.hive and self.hive.rpc:
                logger.info(f"Initialized Hive API with nodes: {self.hive.rpc.urls}")
            else:
                logger.info("Initialized Hive API with unknown nodes")
        except Exception as e:
            logger.error(f"Failed to initialize beem Hive: {e}")
            # Fallback to direct RPC calls
            self.hive = None

    # Start lazy initialization when needed
    def _ensure_initialization_started(self):
        """Ensure initialization process has started, but don't wait for it"""
        if not self.initialized and not self.initializing and _beem_available:
            logger.info("Starting delayed background initialization of Hive API")
            self.initialization_thread = self._async_init_beem()

    # Method for operations that can wait for initialization
    def _ensure_initialized(self, timeout=None):
        """Ensure the API is initialized before proceeding with operations"""
        timeout = timeout or self.initialization_timeout
        self._ensure_initialization_started()

        if self.initialization_thread and not self.initialized:
            logger.info("Waiting for Hive API initialization to complete...")
            self.initialization_thread.join(timeout=timeout)
            if not self.initialized:
                logger.warning(
                    f"Hive API initialization did not complete within {timeout} seconds"
                )

    def get_trending_posts(
        self, limit: int = 20, tag: Optional[str] = None, retries: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get trending posts from the Hive blockchain

        Args:
            limit: Number of posts to fetch
            tag: Optional tag to filter posts
            retries: Number of retry attempts for failed requests

        Returns:
            List of post dictionaries
        """
        # Start initialization in background but don't wait
        self._ensure_initialization_started()

        attempt = 0
        while attempt < retries:
            try:
                # If beem is available and initialized, use it
                if self.hive and self.initialized:
                    try:
                        # Create a query with the specified parameters
                        query = Query(limit=limit, tag=tag or "")

                        # Create a Discussions instance with our hive client
                        discussions = Discussions(blockchain_instance=self.hive)

                        # Get trending discussions
                        trending_iterator = discussions.get_discussions(
                            "trending", query
                        )

                        # Log success to confirm we're using beem
                        logger.info(
                            "Successfully retrieved trending posts using beem, processing results"
                        )

                        # Process results
                        result = []
                        for post in trending_iterator:
                            try:
                                formatted_post = self._format_post(post)
                                if formatted_post:
                                    result.append(formatted_post)
                            except Exception as e:
                                logger.error(f"Error formatting post: {e}")

                        logger.info(
                            f"Returning {len(result)} formatted posts from blockchain"
                        )

                        # Add a field to indicate these are fresh blockchain posts
                        for post in result:
                            post["from_blockchain"] = True

                        return result
                    except Exception as e:
                        logger.error(f"Error with beem Discussions: {e}")
                        # Let's try a direct API call as fallback
                        attempt += 1
                        continue

                # Fallback to REST API - this is the fast path for immediate results
                try:
                    # First try the newer bridge API format
                    response = requests.post(
                        f"{self.api_url}/bridge.get_ranked_posts",
                        json={"sort": "trending", "tag": tag or "", "limit": limit},
                    )

                    if not response.ok:
                        # Fall back to older format
                        params = {"tag": tag or "", "limit": limit}
                        response = requests.post(
                            f"{self.api_url}/get_discussions_by_trending",
                            json=params,
                        )

                    if response.ok:
                        posts_data = response.json()
                        # Handle different response formats
                        if isinstance(posts_data, dict) and "result" in posts_data:
                            posts_data = posts_data["result"]

                        result = []
                        for post in posts_data:
                            if isinstance(post, dict) and "author" in post:
                                formatted_post = self._format_post_from_api(post)
                                if formatted_post:
                                    result.append(formatted_post)

                        logger.info(f"Returning {len(result)} posts from REST API")

                        # Add a field to indicate these are fresh blockchain posts
                        for post in result:
                            post["from_blockchain"] = True

                        return result
                    else:
                        logger.error(
                            f"Failed to fetch trending posts: {response.status_code} - {response.text[:200]}"
                        )
                        attempt += 1
                        time.sleep(1)  # Wait before retrying
                        continue
                except requests.RequestException as e:
                    logger.error(f"Request error fetching trending posts: {e}")
                    attempt += 1
                    time.sleep(1)  # Wait before retrying
                    continue

            except Exception as e:
                logger.exception(f"Error fetching trending posts: {e}")
                attempt += 1
                if attempt < retries:
                    time.sleep(1)  # Wait before retrying
                continue

        # If all attempts failed, return empty list
        logger.error(f"All {retries} attempts to fetch trending posts failed")
        return []

    def get_post(self, author: str, permlink: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific post from the Hive blockchain

        Args:
            author: Post author
            permlink: Post permlink

        Returns:
            Post dictionary or None if not found
        """
        if not author or not permlink:
            logger.error("Author and permlink are required")
            return None

        try:
            if self.hive:
                try:
                    post = Comment(
                        f"@{author}/{permlink}", blockchain_instance=self.hive
                    )
                    formatted_post = self._format_post(post)
                    if formatted_post:
                        return formatted_post
                    return None
                except ContentDoesNotExistsException:
                    logger.warning(f"Post @{author}/{permlink} does not exist")
                    return None
                except Exception as e:
                    logger.error(f"Error with beem Comment: {e}, falling back to API")
                    # Fall through to API method if beem fails

            # Fallback to REST API (or primary method if beem not available)
            try:
                # Try the newer bridge API format first
                response = requests.post(
                    f"{self.api_url}/bridge.get_post",
                    json={"author": author, "permlink": permlink},
                )

                if not response.ok:
                    # Fall back to older format
                    response = requests.post(
                        f"{self.api_url}/get_content",
                        json={"author": author, "permlink": permlink},
                    )

                if response.ok:
                    post_data = response.json()
                    # Handle different response formats
                    if isinstance(post_data, dict) and "result" in post_data:
                        post_data = post_data["result"]

                    # Check if post exists (Hive API returns empty post with id 0 if not found)
                    if not isinstance(post_data, dict) or not post_data.get("body"):
                        logger.warning(f"Post @{author}/{permlink} not found or empty")
                        return None

                    if isinstance(post_data, dict) and post_data.get("id") == 0:
                        logger.warning(f"Post @{author}/{permlink} not found (id=0)")
                        return None

                    formatted_post = self._format_post_from_api(post_data)
                    if formatted_post:
                        return formatted_post
                    return None
                else:
                    logger.error(
                        f"Failed to fetch post: {response.status_code} - {response.text[:200]}"
                    )
                    return None
            except requests.RequestException as e:
                logger.error(f"Request error fetching post: {e}")
                return None

        except Exception as e:
            logger.exception(
                f"Unexpected error fetching post @{author}/{permlink}: {e}"
            )
            return None

    def get_user_profile(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile information from the Hive blockchain

        Args:
            username: Hive username

        Returns:
            User profile dictionary or None if not found
        """
        if not username:
            logger.error("Username is required")
            return None

        try:
            if self.hive:
                try:
                    account = Account(username, blockchain_instance=self.hive)
                    profile = self._format_account(account)
                    return profile
                except AccountDoesNotExistsException:
                    logger.warning(f"Account {username} does not exist")
                    return None
                except Exception as e:
                    logger.error(f"Error with beem Account: {e}, falling back to API")
                    # Fall through to API method if beem fails

            # Fallback to REST API (or primary method if beem not available)
            try:
                # Try the newer bridge API format first
                response = requests.post(
                    f"{self.api_url}/bridge.get_profile", json={"account": username}
                )

                if not response.ok:
                    # Fall back to older format
                    response = requests.post(
                        f"{self.api_url}/get_accounts", json=[username]
                    )

                if response.ok:
                    data = response.json()

                    # Handle different response formats
                    if isinstance(data, dict) and "result" in data:
                        account_data = data["result"]
                    elif isinstance(data, list) and len(data) > 0:
                        account_data = data[0]
                    else:
                        account_data = None

                    if account_data:
                        return self._format_account_from_api(account_data)
                    return None
                else:
                    logger.error(
                        f"Failed to fetch account: {response.status_code} - {response.text}"
                    )
                    return None
            except requests.RequestException as e:
                logger.error(f"Request error fetching account: {e}")
                return None

        except Exception as e:
            logger.exception(f"Unexpected error fetching account {username}: {e}")
            return None

    def get_user_posts(self, username: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get posts by a specific user

        Args:
            username: Hive username
            limit: Number of posts to fetch

        Returns:
            List of post dictionaries
        """
        try:
            if self.hive:
                query = Query(limit=limit, tag=username, start_author=username)
                discussions = Discussions(blockchain_instance=self.hive)
                # Replace .get_blog with get_discussions
                blog_posts = discussions.get_discussions("blog", query)

                result = []
                for post in blog_posts:
                    fp = self._format_post(post)
                    if fp:
                        result.append(fp)
                return result
            else:
                # Fallback to REST API
                params = {"tag": username, "limit": limit}
                response = requests.get(
                    f"{self.api_url}/get_discussions_by_blog", json=params
                )
                if response.ok:
                    return [
                        p
                        for p in map(self._format_post_from_api, response.json())
                        if p is not None
                    ]
                else:
                    logger.error(
                        f"Failed to fetch user posts: {response.status_code} - {response.text}"
                    )
                    return []

        except Exception as e:
            logger.exception(f"Error fetching posts for {username}: {e}")
            return []

    def get_account_history(
        self, username: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get account transaction history

        Args:
            username: Hive username
            limit: Number of history items to fetch

        Returns:
            List of transaction dictionaries
        """
        try:
            if self.hive:
                try:
                    account = Account(username, blockchain_instance=self.hive)
                    history = list(account.get_account_history(index=-1, limit=limit))

                    # Format the history items
                    formatted_history = []
                    for item in history:
                        # Extract operation type
                        op_type = item.get("type", "")
                        if (
                            not op_type
                            and isinstance(item.get("op"), list)
                            and len(item.get("op", [])) > 0
                        ):
                            op_type = item["op"][0]

                        # Extract timestamp
                        timestamp = item.get("timestamp", "")
                        if isinstance(timestamp, str):
                            timestamp_str = timestamp
                        elif hasattr(timestamp, "strftime"):
                            timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            timestamp_str = str(timestamp)

                        # Create base transaction object
                        transaction = {
                            "type": op_type,
                            "timestamp": timestamp_str,
                            "transaction_id": item.get("trx_id", ""),
                        }

                        # Add operation-specific details
                        op_data = {}
                        if isinstance(item.get("op"), list) and len(item["op"]) > 1:
                            op_data = item["op"][1]

                        if op_type == "transfer":
                            transaction["from"] = op_data.get("from", "")
                            transaction["to"] = op_data.get("to", "")
                            transaction["amount"] = op_data.get("amount", "")
                            transaction["memo"] = op_data.get("memo", "")
                            transaction["formatted"] = {
                                "title": f"Transfer: {op_data.get('amount', '')}",
                                "description": f"From {op_data.get('from', '')} to {op_data.get('to', '')}: {op_data.get('memo', '')}",
                                "timestamp": timestamp_str,
                                "type": "transfer",
                            }
                        elif op_type == "claim_reward_balance":
                            transaction["account"] = op_data.get("account", "")
                            transaction["reward_hive"] = op_data.get(
                                "reward_hive", "0.000 HIVE"
                            )
                            transaction["reward_hbd"] = op_data.get(
                                "reward_hbd", "0.000 HBD"
                            )
                            transaction["reward_vests"] = op_data.get(
                                "reward_vests", "0.000000 VESTS"
                            )
                            transaction["formatted"] = {
                                "title": "Claim Rewards",
                                "description": f"{op_data.get('reward_hive', '0.000 HIVE')}, {op_data.get('reward_hbd', '0.000 HBD')}, {op_data.get('reward_vests', '0.000000 VESTS')}",
                                "timestamp": timestamp_str,
                                "type": "claim",
                            }
                        elif op_type == "comment":
                            transaction["author"] = op_data.get("author", "")
                            transaction["permlink"] = op_data.get("permlink", "")
                            transaction["parent_author"] = op_data.get(
                                "parent_author", ""
                            )
                            transaction["parent_permlink"] = op_data.get(
                                "parent_permlink", ""
                            )
                            # Extract title from the first part of body for posts
                            is_post = op_data.get("parent_author", "") == ""
                            if is_post:
                                body = op_data.get("body", "")
                                title_end = min(50, len(body))
                                transaction["title"] = body[:title_end] + (
                                    "..." if len(body) > title_end else ""
                                )
                                transaction["formatted"] = {
                                    "title": f"Post: {op_data.get('title', op_data.get('permlink', ''))}",
                                    "description": "New post",
                                    "timestamp": timestamp_str,
                                    "type": "post",
                                }
                            else:
                                transaction["formatted"] = {
                                    "title": f"Comment: {op_data.get('permlink', '')}",
                                    "description": f"Comment on @{op_data.get('parent_author', '')}/{op_data.get('parent_permlink', '')}",
                                    "timestamp": timestamp_str,
                                    "type": "comment",
                                }
                        elif op_type == "vote":
                            transaction["voter"] = op_data.get("voter", "")
                            transaction["author"] = op_data.get("author", "")
                            transaction["permlink"] = op_data.get("permlink", "")
                            transaction["weight"] = op_data.get("weight", 0)
                            transaction["formatted"] = {
                                "title": f"Vote: {op_data.get('weight', 0)/100}%",
                                "description": f"On @{op_data.get('author', '')}/{op_data.get('permlink', '')}",
                                "timestamp": timestamp_str,
                                "type": "vote",
                            }
                        elif op_type == "delegate_vesting_shares":
                            transaction["delegator"] = op_data.get("delegator", "")
                            transaction["delegatee"] = op_data.get("delegatee", "")
                            transaction["vesting_shares"] = op_data.get(
                                "vesting_shares", ""
                            )
                            transaction["formatted"] = {
                                "title": f"Delegation: {op_data.get('vesting_shares', '')}",
                                "description": f"From {op_data.get('delegator', '')} to {op_data.get('delegatee', '')}",
                                "timestamp": timestamp_str,
                                "type": "delegation",
                            }
                        else:
                            transaction["formatted"] = {
                                "title": f"Operation: {op_type}",
                                "description": "Blockchain operation",
                                "timestamp": timestamp_str,
                                "type": "operation",
                            }

                        # Add the formatted transaction
                        formatted_history.append(transaction)

                    return formatted_history
                except Exception as e:
                    logger.exception(f"Error getting account history with beem: {e}")
                    # Fall through to REST API if beem fails

            # Fall back to REST API or mock data if beem not available
            try:
                # Try to get history via the account_history API
                response = requests.post(
                    f"{self.api_url}/account_history_api.get_account_history",
                    json={"account": username, "start": -1, "limit": limit},
                )

                if response.ok:
                    data = response.json()
                    if (
                        "result" in data
                        and isinstance(data["result"], dict)
                        and "history" in data["result"]
                    ):
                        history = data["result"]["history"]

                        # Format the results
                        formatted_history = []
                        for item in history:
                            if (
                                len(item) >= 2
                                and isinstance(item[1], dict)
                                and "op" in item[1]
                            ):
                                op = item[1]["op"]
                                if isinstance(op, list) and len(op) >= 2:
                                    op_type = op[0]
                                    op_data = op[1]

                                    # Format timestamp
                                    timestamp = item[1].get("timestamp", "")

                                    # Create base transaction
                                    transaction = {
                                        "type": op_type,
                                        "timestamp": timestamp,
                                        "transaction_id": item[1].get("trx_id", ""),
                                    }

                                    # Add operation-specific details
                                    if op_type == "transfer":
                                        transaction["from"] = op_data.get("from", "")
                                        transaction["to"] = op_data.get("to", "")
                                        transaction["amount"] = op_data.get(
                                            "amount", ""
                                        )
                                        transaction["memo"] = op_data.get("memo", "")
                                        transaction["formatted"] = {
                                            "title": f"Transfer: {op_data.get('amount', '')}",
                                            "description": f"From {op_data.get('from', '')} to {op_data.get('to', '')}: {op_data.get('memo', '')}",
                                            "timestamp": timestamp,
                                            "type": "transfer",
                                        }
                                    elif op_type == "claim_reward_balance":
                                        transaction["account"] = op_data.get(
                                            "account", ""
                                        )
                                        transaction["reward_hive"] = op_data.get(
                                            "reward_hive", "0.000 HIVE"
                                        )
                                        transaction["reward_hbd"] = op_data.get(
                                            "reward_hbd", "0.000 HBD"
                                        )
                                        transaction["reward_vests"] = op_data.get(
                                            "reward_vests", "0.000000 VESTS"
                                        )
                                        transaction["formatted"] = {
                                            "title": "Claim Rewards",
                                            "description": f"{op_data.get('reward_hive', '0.000 HIVE')}, {op_data.get('reward_hbd', '0.000 HBD')}, {op_data.get('reward_vests', '0.000000 VESTS')}",
                                            "timestamp": timestamp,
                                            "type": "claim",
                                        }
                                    elif op_type == "comment":
                                        transaction["author"] = op_data.get(
                                            "author", ""
                                        )
                                        transaction["permlink"] = op_data.get(
                                            "permlink", ""
                                        )
                                        transaction["parent_author"] = op_data.get(
                                            "parent_author", ""
                                        )
                                        transaction["parent_permlink"] = op_data.get(
                                            "parent_permlink", ""
                                        )
                                        is_post = op_data.get("parent_author", "") == ""
                                        if is_post:
                                            transaction["formatted"] = {
                                                "title": f"Post: {op_data.get('permlink', '')}",
                                                "description": "New post",
                                                "timestamp": timestamp,
                                                "type": "post",
                                            }
                                        else:
                                            transaction["formatted"] = {
                                                "title": f"Comment: {op_data.get('permlink', '')}",
                                                "description": f"Comment on @{op_data.get('parent_author', '')}/{op_data.get('parent_permlink', '')}",
                                                "timestamp": timestamp,
                                                "type": "comment",
                                            }
                                    elif op_type == "vote":
                                        transaction["voter"] = op_data.get("voter", "")
                                        transaction["author"] = op_data.get(
                                            "author", ""
                                        )
                                        transaction["permlink"] = op_data.get(
                                            "permlink", ""
                                        )
                                        transaction["weight"] = op_data.get("weight", 0)
                                        transaction["formatted"] = {
                                            "title": f"Vote: {op_data.get('weight', 0)/100}%",
                                            "description": f"On @{op_data.get('author', '')}/{op_data.get('permlink', '')}",
                                            "timestamp": timestamp,
                                            "type": "vote",
                                        }
                                    else:
                                        transaction["formatted"] = {
                                            "title": f"Operation: {op_type}",
                                            "description": "Blockchain operation",
                                            "timestamp": timestamp,
                                            "type": "operation",
                                        }

                                    formatted_history.append(transaction)

                        return formatted_history

                # If we get here, fall back to mock data
                logger.warning(
                    "Failed to get account history through API, using mock data"
                )
                return self._get_mock_account_history(username, limit)
            except Exception as e:
                logger.exception(f"Error getting account history via API: {e}")
                return self._get_mock_account_history(username, limit)

        except Exception as e:
            logger.exception(f"Error getting account history: {e}")
            return self._get_mock_account_history(username, limit)

    def get_user_wallet(self, username: str) -> Dict[str, Any]:
        """
        Get user wallet information

        Args:
            username: Hive username

        Returns:
            Wallet information dictionary
        """
        try:
            if self.hive:
                account = Account(username, blockchain_instance=self.hive)

                # Get balances and convert to proper format
                balances = {
                    "username": username,
                    "hive_balance": str(account.get("balance")),
                    "hbd_balance": str(account.get("hbd_balance")),
                    "hive_power": self._calculate_hive_power(account),
                    "savings_hive": str(account.get("savings_balance")),
                    "savings_hbd": str(account.get("savings_hbd_balance")),
                    "vesting_shares": str(account.get("vesting_shares")),
                    "delegated_vesting_shares": str(
                        account.get("delegated_vesting_shares")
                    ),
                    "received_vesting_shares": str(
                        account.get("received_vesting_shares")
                    ),
                    "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }

                return balances
            else:
                # Fallback to REST API
                response = requests.get(f"{self.api_url}/get_accounts", json=[username])
                if response.ok:
                    accounts = response.json()
                    if accounts and len(accounts) > 0:
                        account = accounts[0]
                        return {
                            "username": username,
                            "hive_balance": account.get("balance"),
                            "hbd_balance": account.get("hbd_balance"),
                            "hive_power": "Unknown (API limitation)",
                            "savings_hive": account.get("savings_balance"),
                            "savings_hbd": account.get("savings_hbd_balance"),
                            "vesting_shares": account.get("vesting_shares"),
                            "delegated_vesting_shares": account.get(
                                "delegated_vesting_shares"
                            ),
                            "received_vesting_shares": account.get(
                                "received_vesting_shares"
                            ),
                            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }
                    else:
                        logger.error(f"Account {username} not found")
                        return self._get_mock_wallet(username)
                else:
                    logger.error(
                        f"Failed to fetch account: {response.status_code} - {response.text}"
                    )
                    return self._get_mock_wallet(username)

        except Exception as e:
            logger.exception(f"Error fetching wallet for {username}: {e}")
            return self._get_mock_wallet(username)

    def broadcast_transaction(
        self, operation_name: str, operation_data: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Broadcast a transaction to the Hive blockchain

        Args:
            operation_name: The name of the operation to broadcast
            operation_data: The data for the operation

        Returns:
            Tuple of (success, result) where result contains transaction details or error
        """
        # For critical operations, ensure initialization is complete
        self._ensure_initialized()

        try:
            if not self.hive:
                return False, {"error": "Hive instance not initialized"}

            # Create a new transaction
            tx = self.hive.new_tx()

            # Add the operation
            tx.appendOps({"type": operation_name, **operation_data})

            # Broadcast the transaction
            result = tx.broadcast()
            if result is not None and "id" in result:
                return True, {"transaction_id": result["id"], "details": result}
            else:
                logger.error("Broadcast returned None or missing 'id' in result")
                return False, {"error": "Broadcast failed: no transaction id returned"}

        except Exception as e:
            logger.exception(f"Error broadcasting transaction: {e}")
            return False, {"error": str(e)}

    def get_transaction(self, tx_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a transaction by its ID

        Args:
            tx_id: Transaction ID

        Returns:
            Transaction details or None if not found
        """
        try:
            if self.hive and hasattr(self.hive, "rpc") and self.hive.rpc:
                tx = self.hive.rpc.get_transaction(tx_id)
                return tx
            else:
                # Fallback to REST API
                response = requests.post(
                    f"{self.api_url}/get_transaction", json={"id": tx_id}
                )
                if response.ok:
                    return response.json()
                else:
                    logger.error(
                        f"Failed to fetch transaction: {response.status_code} - {response.text}"
                    )
                    return None
        except Exception as e:
            logger.exception(f"Error fetching transaction {tx_id}: {e}")
            return None

    def _format_transaction(self, tx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Format a raw transaction into a more user-friendly format

        Args:
            tx: Raw transaction from the blockchain

        Returns:
            Formatted transaction or None if invalid
        """
        try:
            if not tx or "operations" not in tx:
                return None

            # Get the first operation (most transactions only have one)
            operations = tx.get("operations", [])
            if (
                not operations
                or not isinstance(operations, list)
                or len(operations) == 0
            ):
                return None

            op = operations[0]
            if not isinstance(op, list) or len(op) < 2:
                return None

            op_type = op[0]
            op_data = op[1]

            formatted_tx = {
                "type": op_type,
                "timestamp": tx.get("expiration", ""),
                "transaction_id": tx.get("transaction_id", ""),
            }

            # Add operation-specific details
            if op_type == "transfer":
                formatted_tx["from"] = op_data.get("from", "")
                formatted_tx["to"] = op_data.get("to", "")
                formatted_tx["amount"] = op_data.get("amount", "")
                formatted_tx["memo"] = op_data.get("memo", "")
            elif op_type == "claim_reward_balance":
                formatted_tx["account"] = op_data.get("account", "")
                formatted_tx["reward_hive"] = op_data.get("reward_hive", "")
                formatted_tx["reward_hbd"] = op_data.get("reward_hbd", "")
                formatted_tx["reward_vests"] = op_data.get("reward_vests", "")
            elif op_type == "comment":
                formatted_tx["author"] = op_data.get("author", "")
                formatted_tx["permlink"] = op_data.get("permlink", "")
                formatted_tx["parent_author"] = op_data.get("parent_author", "")
            elif op_type == "vote":
                formatted_tx["voter"] = op_data.get("voter", "")
                formatted_tx["author"] = op_data.get("author", "")
                formatted_tx["permlink"] = op_data.get("permlink", "")
                formatted_tx["weight"] = op_data.get("weight", 0)

            return formatted_tx

        except Exception as e:
            logger.error(f"Error formatting transaction: {e}")
            return None

    def _format_post(self, post) -> Optional[Dict[str, Any]]:
        """
        Format a beem Comment object into a standardized post dictionary

        Args:
            post: Beem Comment object

        Returns:
            Formatted post dictionary or None if formatting fails
        """
        try:
            # Ensure we have the minimum required fields
            if not hasattr(post, "json") and not isinstance(post, dict):
                logger.error(f"Invalid post object received: {type(post)}")
                return None

            # Get created date safely
            if (
                not isinstance(post, dict)
                and hasattr(post, "json")
                and callable(post.json)
            ):
                try:
                    post_json = post.json()
                    if isinstance(post_json, dict):
                        created = post_json.get("created", "")
                        # Also get author/permlink from json if available
                        author = post_json.get("author", "")
                        permlink = post_json.get("permlink", "")
                    else:
                        created = getattr(post_json, "created", "")
                        author = getattr(post_json, "author", "")
                        permlink = getattr(post_json, "permlink", "")
                except Exception as e:
                    logger.error(f"Error calling post.json(): {e}")
                    created = ""
                    # Try to get from post directly
                    author = post.get("author", "") if hasattr(post, "get") else ""
                    permlink = post.get("permlink", "") if hasattr(post, "get") else ""
            else:
                # Treat post as dictionary if it already is one
                created = post.get("created", "") if isinstance(post, dict) else ""
                author = post.get("author", "") if isinstance(post, dict) else ""
                permlink = post.get("permlink", "") if isinstance(post, dict) else ""

            # If still no author/permlink, check attributes directly for non-dict objects
            if not author and not isinstance(post, dict) and hasattr(post, "author"):
                author = post.author
            if (
                not permlink
                and not isinstance(post, dict)
                and hasattr(post, "permlink")
            ):
                permlink = post.permlink

            if not author or not permlink:
                logger.error("Post missing required author/permlink")
                return None

            # Extract metadata safely
            json_metadata = {}
            try:
                if (
                    not isinstance(post, dict)
                    and hasattr(post, "json_metadata")
                    and not callable(getattr(post, "json_metadata", None))
                ):
                    json_metadata = post.json_metadata
                elif (
                    not isinstance(post, dict)
                    and hasattr(post, "json")
                    and callable(post.json)
                ):
                    post_json = post.json()
                    if isinstance(post_json, dict):
                        json_metadata = post_json.get("json_metadata", {})
                    else:
                        json_metadata = {}
                else:
                    json_metadata = (
                        post.get("json_metadata", {}) if hasattr(post, "get") else {}
                    )

                # Parse JSON metadata if it's a string
                if isinstance(json_metadata, str):
                    json_metadata = json.loads(json_metadata)
            except (json.JSONDecodeError, AttributeError, Exception) as e:
                logger.warning(f"Error parsing json_metadata: {e}")
                json_metadata = {}

            # Get images from json_metadata
            images = json_metadata.get("images", [])
            image = images[0] if images else None

            # Initialize tags list first to avoid scope issues
            tags = []

            # Extract tags from json_metadata
            if json_metadata and "tags" in json_metadata:
                tags = json_metadata.get("tags", [])

            # If no tags in json_metadata, try to get from category
            if not tags and not isinstance(post, dict) and hasattr(post, "category"):
                category = post.category
                if category:
                    tags = [category]
            elif not tags and isinstance(post, dict) and "category" in post:
                tags = [post.get("category")]

            # Get vote count safely
            active_votes = []
            if isinstance(post, dict):
                active_votes = post.get("active_votes", [])
            elif hasattr(post, "active_votes"):
                active_votes = post.active_votes

            # Get vote count safely
            vote_count = len(active_votes) if isinstance(active_votes, list) else 0

            # Create a safe post ID
            post_id = f"@{author}/{permlink}"

            # Get other fields safely with proper fallbacks
            title = ""
            body = ""
            category = ""
            depth = 0
            children = 0

            if hasattr(post, "title") and not isinstance(post, dict):
                title = post.title
            elif isinstance(post, dict):
                title = post.get("title", "")

            if isinstance(post, dict):
                body = post.get("body", "")
            elif hasattr(post, "body"):
                body = post.body
            else:
                body = ""

            if not isinstance(post, dict) and hasattr(post, "category"):
                category = post.category
            elif isinstance(post, dict):
                category = post.get("category", "")
            else:
                category = ""

            if hasattr(post, "children"):
                children = int(getattr(post, "children", 0))
            elif isinstance(post, dict):
                children = int(post.get("children", 0))

            # Format payout values
            def format_payout(value):
                if not value:
                    return "0.000 HBD"
                if isinstance(value, (int, float)):
                    return f"{value:.3f} HBD"
                return str(value)

            # Build the formatted post
            formatted_post = {
                "id": post_id,
                "author": author,
                "permlink": permlink,
                "title": title,
                "body": body,
                "created": created,
                "category": category,
                "depth": depth,
                "children": children,
                "vote_count": vote_count,
                "comment_count": children,
                "payout": format_payout(
                    getattr(post, "pending_payout_value", None)
                    if hasattr(post, "pending_payout_value")
                    else (
                        post.get("pending_payout_value", "0.000 HBD")
                        if isinstance(post, dict)
                        else "0.000 HBD"
                    )
                ),
                "tags": tags,
                "image": image,
                "json_metadata": json_metadata,
            }

            return formatted_post
        except Exception as e:
            logger.error(f"Error formatting post: {e}")
            return None

    def _format_post_from_api(
        self, post_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Format a raw API post into a standardized post dictionary

        Args:
            post_data: Raw API post data

        Returns:
            Formatted post dictionary or None if formatting fails
        """
        if not isinstance(post_data, dict):
            logger.error(f"Invalid post data type: {type(post_data)}")
            return None

        try:
            # Extract required fields safely
            author = post_data.get("author", "")
            permlink = post_data.get("permlink", "")

            if not author or not permlink:
                logger.error(
                    f"Post missing required author/permlink: {post_data.keys()}"
                )
                return None

            # Handle json_metadata which can be a string or already parsed
            json_metadata = {}
            try:
                json_metadata_raw = post_data.get("json_metadata", {})
                if isinstance(json_metadata_raw, str) and json_metadata_raw.strip():
                    json_metadata = json.loads(json_metadata_raw)
                elif isinstance(json_metadata_raw, dict):
                    json_metadata = json_metadata_raw
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse json_metadata: {e}")

            # Get images from json_metadata
            images = json_metadata.get("images", [])
            image = images[0] if images else None

            # Extract tags
            tags = json_metadata.get("tags", [])
            if not tags and post_data.get("category"):
                tags = [post_data.get("category")]

            # Handle cases where active_votes might be a string or other non-list type
            active_votes = []
            try:
                votes_raw = post_data.get("active_votes", [])
                if isinstance(votes_raw, str) and votes_raw.strip():
                    active_votes = json.loads(votes_raw)
                elif isinstance(votes_raw, list):
                    active_votes = votes_raw
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Error parsing active_votes: {e}")

            # Parse numeric fields safely
            def safe_int(value, default=0):
                try:
                    if value is None:
                        return default
                    return int(value)
                except (ValueError, TypeError):
                    return default

            depth = safe_int(post_data.get("depth"))
            children = safe_int(post_data.get("children"))
            net_votes = safe_int(post_data.get("net_votes"))

            # Ensure all required fields have valid values
            title = post_data.get("title", "")
            body = post_data.get("body", "")
            created = post_data.get("created", "")
            category = post_data.get("category", "")

            # Format payout values
            def format_payout(value):
                if not value:
                    return "0.000 HBD"
                if isinstance(value, (int, float)):
                    return f"{value:.3f} HBD"
                return str(value)

            return {
                "id": f"@{author}/{permlink}",
                "author": author,
                "permlink": permlink,
                "title": title,
                "body": body,
                "created": created,
                "category": category,
                "depth": depth,
                "children": children,
                "net_votes": net_votes,
                "vote_count": len(active_votes),
                "comment_count": children,
                "max_accepted_payout": format_payout(
                    post_data.get("max_accepted_payout")
                ),
                "pending_payout_value": format_payout(
                    post_data.get("pending_payout_value")
                ),
                "payout": format_payout(post_data.get("pending_payout_value")),
                "curator_payout_value": format_payout(
                    post_data.get("curator_payout_value")
                ),
                "promoted": format_payout(post_data.get("promoted")),
                "replies": [],  # This would be populated separately if needed
                "tags": tags,
                "image": image,
                "json_metadata": json_metadata,
            }
        except Exception as e:
            logger.error(f"Error formatting post from API: {e}")
            return None

    def _format_account(self, account: Any) -> Dict[str, Any]:
        """
        Format a beem Account object into a standardized profile dictionary

        Args:
            account: Beem Account object

        Returns:
            Formatted profile dictionary
        """
        if hasattr(account, "json"):
            acc_data = account.json()
        else:
            acc_data = account  # assume dict
        # Extract profile from json_metadata
        json_metadata = acc_data.get("json_metadata", {})
        if isinstance(json_metadata, str):
            try:
                json_metadata = json.loads(json_metadata)
            except json.JSONDecodeError:
                json_metadata = {}

        profile = json_metadata.get("profile", {})

        # Get reputation score
        reputation = account.rep

        # Calculate followers and following counts
        following_count = 0
        follower_count = 0
        try:
            following_count = account.get_follow_count().get("following_count", 0)
            follower_count = account.get_follow_count().get("follower_count", 0)
        except Exception as e:
            logger.warning(f"Failed to get follow counts for {account.name}: {e}")

        return {
            "username": account.name,
            "name": profile.get("name", account.name),
            "about": profile.get("about", ""),
            "website": profile.get("website", ""),
            "location": profile.get("location", ""),
            "profile_image": profile.get(
                "profile_image", f"https://images.hive.blog/u/{account.name}/avatar"
            ),
            "cover_image": profile.get("cover_image", ""),
            "followers": follower_count,
            "following": following_count,
            "post_count": account.json().get("post_count", 0),
            "reputation": str(reputation),
            "join_date": account["created"].strftime("%Y-%m-%d"),
            "json_metadata": json_metadata,
            "profile": profile,
        }

    def _format_account_from_api(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a raw API account into a standardized profile dictionary

        Args:
            account_data: Raw API account data

        Returns:
            Formatted profile dictionary
        """
        # Extract profile from json_metadata
        json_metadata = account_data.get("json_metadata", {})
        if isinstance(json_metadata, str):
            try:
                json_metadata = json.loads(json_metadata)
            except json.JSONDecodeError:
                json_metadata = {}

        profile = json_metadata.get("profile", {})
        username = account_data.get("name", "")

        # In the API fallback, we don't have easy access to followers/following
        # These would need separate API calls

        return {
            "username": username,
            "name": profile.get("name", username),
            "about": profile.get("about", ""),
            "website": profile.get("website", ""),
            "location": profile.get("location", ""),
            "profile_image": profile.get(
                "profile_image", f"https://images.hive.blog/u/{username}/avatar"
            ),
            "cover_image": profile.get("cover_image", ""),
            "followers": 0,  # Would need a separate API call
            "following": 0,  # Would need a separate API call
            "post_count": account_data.get("post_count", 0),
            "reputation": "Unknown",  # Requires calculation
            "join_date": account_data.get("created", ""),
            "json_metadata": json_metadata,
            "profile": profile,
        }

    def _calculate_hive_power(self, account: Any) -> str:
        """
        Placeholder logic replacing account.get_hive_power() usage.
        """
        try:
            # ...you can implement your own HP calculation...
            hp = 0.0  # Minimal fallback
            return f"{hp:.3f} HP"
        except Exception as e:
            logger.warning(f"Failed to calculate Hive Power for {account.name}: {e}")
            return "0.000 HP"

    def _get_mock_account_history(
        self, username: str, limit: int
    ) -> List[Dict[str, Any]]:
        """
        Generate mock account history for testing

        Args:
            username: Hive username
            limit: Number of history items to generate

        Returns:
            List of mock transaction dictionaries
        """
        history = []

        # Generate some random transactions
        for i in range(min(limit, 20)):
            timestamp = datetime.now().timestamp() - (
                86400 * i / 2
            )  # Spread over recent days
            dt = datetime.fromtimestamp(timestamp)
            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")

            # Different transaction types
            if i % 5 == 0:
                # Transfer
                history.append(
                    {
                        "type": "transfer",
                        "from": "user" + str(i),
                        "to": username,
                        "amount": f"{(i+1) * 1.5:.3f} HIVE",
                        "memo": f"Payment for services #{i}",
                        "timestamp": dt,
                        "formatted": {
                            "title": f"Transfer: {(i+1) * 1.5:.3f} HIVE",
                            "description": f"From user{i} to {username}: Payment for services #{i}",
                            "timestamp": formatted_time,
                            "type": "transfer",
                        },
                    }
                )
            elif i % 5 == 1:
                # Vote
                history.append(
                    {
                        "type": "vote",
                        "voter": username,
                        "author": "user" + str(i),
                        "permlink": f"post-{i}",
                        "weight": int(min(10000, i * 1000)),
                        "timestamp": dt,
                        "formatted": {
                            "title": f"Vote: {min(100, i * 10):.0f}%",
                            "description": f"On @user{i}/post-{i}",
                            "timestamp": formatted_time,
                            "type": "vote",
                        },
                    }
                )
            elif i % 5 == 2:
                # Comment
                history.append(
                    {
                        "type": "comment",
                        "parent_author": "user" + str(i),
                        "parent_permlink": f"post-{i}",
                        "author": username,
                        "permlink": f"comment-{i}",
                        "title": "",
                        "body": f"This is a comment on post {i}",
                        "timestamp": dt,
                        "formatted": {
                            "title": f"Comment: comment-{i}",
                            "description": f"Comment on @user{i}/post-{i}",
                            "timestamp": formatted_time,
                            "type": "comment",
                        },
                    }
                )
            elif i % 5 == 3:
                # Post
                history.append(
                    {
                        "type": "comment",
                        "parent_author": "",
                        "parent_permlink": "hive",
                        "author": username,
                        "permlink": f"post-{i}",
                        "title": f"My Post {i}",
                        "body": f"This is my post {i}",
                        "timestamp": dt,
                        "formatted": {
                            "title": f"Post: My Post {i}",
                            "description": "New post",
                            "timestamp": formatted_time,
                            "type": "post",
                        },
                    }
                )
            else:
                # Claim reward
                history.append(
                    {
                        "type": "claim_reward_balance",
                        "account": username,
                        "reward_hive": f"{i * 0.1:.3f} HIVE",
                        "reward_hbd": f"{i * 0.05:.3f} HBD",
                        "reward_vests": f"{i * 50:.6f} VESTS",
                        "timestamp": dt,
                        "formatted": {
                            "title": "Claim Rewards",
                            "description": f"{i * 0.1:.3f} HIVE, {i * 0.05:.3f} HBD, {i * 50:.6f} VESTS",
                            "timestamp": formatted_time,
                            "type": "claim",
                        },
                    }
                )

        return history

    def _get_mock_wallet(self, username: str) -> Dict[str, Any]:
        """
        Generate mock wallet data for testing

        Args:
            username: Hive username

        Returns:
            Mock wallet dictionary
        """
        # Generate some realistic looking balances
        return {
            "username": username,
            "hive_balance": "100.000 HIVE",
            "hbd_balance": "250.000 HBD",
            "hive_power": "5000.000 HP",
            "savings_hive": "50.000 HIVE",
            "savings_hbd": "100.000 HBD",
            "vesting_shares": "10000.000000 VESTS",
            "delegated_vesting_shares": "0.000000 VESTS",
            "received_vesting_shares": "0.000000 VESTS",
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def get_recent_transactions(
        self, block_num: Optional[int] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent transactions from the blockchain

        Args:
            block_num: Optional block number to start from (default: latest)
            limit: Number of transactions to fetch

        Returns:
            List of transaction dictionaries
        """
        try:
            if self.hive:
                if block_num is None:
                    # Get current block number
                    props = self.hive.get_dynamic_global_properties()
                    if props is not None and "head_block_number" in props:
                        block_num = props["head_block_number"]
                    else:
                        logger.error(
                            "Unable to retrieve head_block_number from dynamic global properties"
                        )
                        return []

                formatted_transactions = []
                transactions_count = 0
                blocks_checked = 0
                max_blocks_to_check = (
                    5  # Limit how many blocks we check to avoid excessive processing
                )

                # Get the block safely checking if rpc is available
                if not self.hive.rpc:
                    logger.error("Hive RPC is not available, falling back to REST API")
                    response = requests.post(
                        f"{self.api_url}/get_block",
                        json={"block_num": block_num if block_num else "latest"},
                    )
                    if response.ok:
                        block = response.json()
                        if block and "transactions" in block:
                            raw_transactions = block["transactions"][:limit]
                            for tx in raw_transactions:
                                formatted_tx = self._format_transaction(tx)
                                if formatted_tx:
                                    formatted_transactions.append(formatted_tx)
                    return formatted_transactions

                # Use RPC to get blocks and transactions
                current_block_num = block_num

                while (
                    transactions_count < limit
                    and blocks_checked < max_blocks_to_check
                    and current_block_num is not None
                    and current_block_num > 0
                ):
                    try:
                        block = self.hive.rpc.get_block(current_block_num)
                        blocks_checked += 1

                        if block and "transactions" in block:
                            for tx in block["transactions"]:
                                formatted_tx = self._format_transaction(tx)
                                if formatted_tx:
                                    formatted_tx["block_num"] = current_block_num
                                    formatted_transactions.append(formatted_tx)
                                    transactions_count += 1

                                    if transactions_count >= limit:
                                        break
                    except Exception as e:
                        logger.error(f"Error getting block {current_block_num}: {e}")

                    # Move to previous block
                    current_block_num -= 1

                return formatted_transactions[:limit]
            else:
                logger.error("Hive instance not available")
                return []

        except Exception as e:
            logger.exception(f"Error fetching recent transactions: {e}")
            return []

    def _make_api_request(self, endpoint, data):
        """
        Make an API request to the Hive blockchain

        Args:
            endpoint: API endpoint to call
            data: JSON data to send with the request

        Returns:
            API response as a dictionary or None if the request fails
        """
        try:
            response = requests.post(f"{self.api_url}/{endpoint}", json=data)
            if response.ok:
                return response.json()
            else:
                logger.error(
                    f"API request to {endpoint} failed: {response.status_code} - {response.text[:200]}"
                )
                return None
        except requests.RequestException as e:
            logger.error(f"Request error in API request to {endpoint}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error in API request to {endpoint}: {e}")
            return None

    def get_comments(self, author, permlink):
        """
        Get comments for a specific post

        Args:
            author: Post author
            permlink: Post permlink

        Returns:
            List of comment dictionaries
        """
        # First check if we have local comments for this post in our database
        import database as db

        local_comments = db.get_comments_for_post(author, permlink)

        # If we're using the API-only mode or have demo posts, just return local comments
        if local_comments or not _beem_available:
            return local_comments

        # Ensure initialization
        self._ensure_initialization_started()

        comments = []
        try:
            # Use direct API if Beem is not ready yet
            if not self.hive or not self.initialized:
                # Fallback to direct API call
                response = self._make_api_request(
                    "bridge.get_discussion", {"author": author, "permlink": permlink}
                )

                if isinstance(response, dict) and "result" in response:
                    discussion = response["result"]
                    # Extract comments from discussion
                    for key, value in discussion.items():
                        if key != f"@{author}/{permlink}" and "parent_author" in value:
                            comment = self._format_comment(value)
                            comments.append(comment)
            else:
                # Use Beem for better performance
                # Create a dummy Comment object to get replies
                from beem.comment import Comment
                from beem.discussions import Discussions, Query

                post = Comment(f"@{author}/{permlink}", blockchain_instance=self.hive)

                # Get replies
                replies = post.get_all_replies()
                for reply in replies:
                    comment = {
                        "id": reply.authorperm,
                        "author": reply["author"],
                        "permlink": reply["permlink"],
                        "parent_author": reply["parent_author"],
                        "parent_permlink": reply["parent_permlink"],
                        "body": reply.body,
                        "created": reply["created"].strftime("%Y-%m-%dT%H:%M:%S"),
                        "depth": reply["depth"],
                        "children": reply["children"],
                        "net_votes": reply["net_votes"],
                    }
                    comments.append(comment)

            return comments
        except Exception as e:
            logger.error(f"Error fetching comments for {author}/{permlink}: {e}")
            return []

    def _format_comment(self, comment_data):
        """Format comment data from API response"""
        return {
            "id": comment_data.get("authorperm", comment_data.get("id", "")),
            "author": comment_data.get("author", ""),
            "permlink": comment_data.get("permlink", ""),
            "parent_author": comment_data.get("parent_author", ""),
            "parent_permlink": comment_data.get("parent_permlink", ""),
            "body": comment_data.get("body", ""),
            "created": comment_data.get(
                "created", datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            ),
            "depth": comment_data.get("depth", 1),
            "children": comment_data.get("children", 0),
            "net_votes": comment_data.get("net_votes", 0),
        }


# Create a global instance for app-wide use
_hive_api_instance = None


def init_hive_api(api_url: Optional[str] = None) -> HiveAPI:
    """
    Initialize the global HiveAPI instance

    Args:
        api_url: Optional custom API endpoint URL

    Returns:
        HiveAPI instance
    """
    global _hive_api_instance
    _hive_api_instance = HiveAPI(api_url)
    # Don't start initialization here - it will be started lazily when needed
    return _hive_api_instance


def get_hive_api() -> HiveAPI:
    """
    Get the global HiveAPI instance, initializing it if necessary

    Returns:
        HiveAPI instance
    """
    global _hive_api_instance
    if _hive_api_instance is None:
        # Auto-initialize with defaults
        _hive_api_instance = HiveAPI()
    return _hive_api_instance
