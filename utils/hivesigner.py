"""
HiveSigner utility functions for HiveBuzz
Handles authentication with HiveSigner service
"""

import logging
import requests
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlencode

# Configure logging
logger = logging.getLogger(__name__)


class HiveSigner:
    """
    Class to handle HiveSigner authentication and API calls
    """

    def __init__(
        self,
        client_id: str,
        client_secret: Optional[str] = None,
        app_name: str = "hivebuzz",
    ):
        """
        Initialize with application details

        Args:
            client_id: HiveSigner client ID (usually the app name)
            client_secret: Optional client secret for secure token exchange
            app_name: The app name displayed to users
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.app_name = app_name
        self.base_url = "https://hivesigner.com"
        self.api_url = "https://api.hivesigner.com"

    def get_authorize_url(
        self,
        redirect_uri: str,
        scope: Optional[list] = None,
        state: Optional[str] = None,
    ) -> str:
        """
        Generate HiveSigner login URL

        Args:
            redirect_uri: URL to redirect to after authentication
            scope: List of permissions to request
            state: Optional state parameter for OAuth flow

        Returns:
            Login URL to redirect to
        """
        scope = scope or ["login"]

        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": ",".join(scope),
        }

        if state:
            params["state"] = state

        auth_url = f"{self.base_url}/oauth2/authorize?{urlencode(params)}"
        return auth_url

    def get_token(self, code: str, redirect_uri: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Exchange authorization code for access token

        Args:
            code: Authorization code from HiveSigner callback
            redirect_uri: Must match the redirect URI used in authorize URL

        Returns:
            Tuple of (success, result) where result has token details or error
        """
        try:
            params = {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.client_id,
                "redirect_uri": redirect_uri,
            }

            # Add client secret if available
            if self.client_secret:
                params["client_secret"] = self.client_secret

            # Log the request details for debugging
            logger.info(
                f"HiveSigner token request: URL={self.api_url}/oauth2/token, params={params}, redirect_uri={redirect_uri}"
            )

            response = requests.post(f"{self.api_url}/oauth2/token", data=params)

            # Log the response for debugging
            logger.info(
                f"HiveSigner response: Status={response.status_code}, Content-Type={response.headers.get('content-type')}"
            )

            logger.info(f"Response body preview: {response.text[:200]}")

            if response.ok:
                # Make sure we have valid JSON before trying to parse it
                content_type = response.headers.get("content-type", "")
                if "json" in content_type:
                    try:
                        return True, response.json()
                    except ValueError as e:
                        logger.error(f"Failed to parse JSON response: {e}")
                        logger.error(
                            f"Response text: {response.text[:500]}"
                        )  # Log first 500 chars to avoid huge logs
                        return False, {
                            "error": "Invalid JSON in response",
                            "details": str(e),
                        }
                else:
                    # Not JSON response, use text
                    logger.warning(f"Non-JSON response received: {response.text[:500]}")
                    return False, {
                        "error": "Non-JSON response",
                        "details": response.text[:500],
                    }
            else:
                logger.error(
                    f"Failed to get token: {response.status_code} - {response.text[:500]}"
                )
                return False, {
                    "error": f"Request failed with status {response.status_code}",
                    "details": response.text[:500],
                }

        except Exception as e:
            logger.exception("Exception during token exchange")
            return False, {"error": str(e)}

    def verify_token(self, access_token: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify an access token and get user info

        Args:
            access_token: HiveSigner access token

        Returns:
            Tuple of (success, result) where result has user data or error
        """
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(f"{self.api_url}/me", headers=headers)

            if response.ok:
                return True, response.json()
            else:
                logger.error(
                    f"Failed to verify token: {response.status_code} - {response.text}"
                )
                return False, {
                    "error": "Failed to verify token",
                    "details": response.text,
                }

        except Exception as e:
            logger.exception("Exception during token verification")
            return False, {"error": str(e)}

    def refresh_token(self, refresh_token: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Refresh an access token

        Args:
            refresh_token: HiveSigner refresh token

        Returns:
            Tuple of (success, result) where result has new token details or error
        """
        try:
            params = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.client_id,
            }

            # Add client secret if available
            if self.client_secret:
                params["client_secret"] = self.client_secret

            response = requests.post(f"{self.api_url}/oauth2/token", data=params)

            if response.ok:
                return True, response.json()
            else:
                logger.error(
                    f"Failed to refresh token: {response.status_code} - {response.text}"
                )
                return False, {
                    "error": "Failed to refresh token",
                    "details": response.text,
                }

        except Exception as e:
            logger.exception("Exception during token refresh")
            return False, {"error": str(e)}

    def revoke_token(self, access_token: str) -> bool:
        """
        Revoke an access token

        Args:
            access_token: HiveSigner access token to revoke

        Returns:
            Boolean indicating success
        """
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.post(
                f"{self.api_url}/oauth2/token/revoke", headers=headers
            )

            return response.ok

        except Exception as e:
            logger.exception("Exception during token revocation")
            return False


# Create a global instance for app-wide use
hivesigner_client = None


def init_hivesigner(
    client_id: str, client_secret: Optional[str] = None, app_name: str = "hivebuzz"
) -> HiveSigner:
    """
    Initialize HiveSigner client with app details

    Args:
        client_id: HiveSigner client ID
        client_secret: Optional client secret
        app_name: The app name

    Returns:
        HiveSigner instance
    """
    global hivesigner_client
    hivesigner_client = HiveSigner(client_id, client_secret, app_name)
    return hivesigner_client


def get_hivesigner_client() -> Optional[HiveSigner]:
    """
    Get the global HiveSigner client instance

    Returns:
        HiveSigner instance or None if not initialized
    """
    return hivesigner_client
