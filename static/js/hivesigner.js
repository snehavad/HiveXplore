/**
 * HiveSigner Helper functions
 * For integrating with HiveSigner (formerly SteemConnect) OAuth
 */
const HiveSigner = {
	/**
	 * Initialize HiveSigner with configuration
	 * @param {Object} config - Configuration object
	 * @param {string} config.clientId - App name registered on HiveSigner
	 * @param {string} config.callbackUrl - URL to redirect after authentication
	 * @param {string} config.scope - Requested permission scopes
	 * @returns {Object} - The HiveSigner instance
	 */
	init: function (config = {}) {
		this.clientId = config.clientId || "hivebuzz";
		this.callbackUrl =
			config.callbackUrl ||
			`${window.location.origin}/hivesigner/callback`;
		this.scope = config.scope || "login,vote,comment,offline";
		this.baseAuthUrl = "https://hivesigner.com/oauth2/authorize";
		this.baseApiUrl = "https://hivesigner.com/api";
		return this;
	},

	/**
	 * Generate authorization URL for HiveSigner login
	 * @param {string} username - Optional username to pre-fill
	 * @param {string} state - Optional state parameter for security
	 * @returns {string} - URL to redirect user for HiveSigner login
	 */
	getAuthUrl: function (username = "", state = "") {
		let authUrl = `${this.baseAuthUrl}?client_id=${
			this.clientId
		}&redirect_uri=${encodeURIComponent(
			this.callbackUrl
		)}&scope=${encodeURIComponent(this.scope)}&response_type=code`;

		if (username) {
			authUrl += `&username=${encodeURIComponent(username)}`;
		}

		if (state) {
			authUrl += `&state=${encodeURIComponent(state)}`;
			// Save state in localStorage for validation on callback
			localStorage.setItem("hivesigner_state", state);
		}

		return authUrl;
	},

	/**
	 * Redirect user to HiveSigner login
	 * @param {string} username - Optional username to pre-fill
	 */
	login: function (username = "") {
		// Generate random state for security
		const state = Math.random().toString(36).substring(2, 15);
		const authUrl = this.getAuthUrl(username, state);
		window.location.href = authUrl;
	},

	/**
	 * Process the callback from HiveSigner
	 * @param {string} code - Authorization code from callback URL
	 * @param {string} state - State parameter from callback URL
	 * @returns {Promise} - Promise that resolves with the authentication result
	 */
	handleCallback: function (code, state) {
		// Verify state matches for security (CSRF protection)
		const savedState = localStorage.getItem("hivesigner_state");
		if (state && savedState && state !== savedState) {
			return Promise.reject(new Error("Invalid state parameter"));
		}

		// Clear state after validation
		localStorage.removeItem("hivesigner_state");

		// In a real app, you would exchange code for access token on your server
		// For this demo, we'll just return the code
		return Promise.resolve({ success: true, code });
	},
};

// Make it globally available
window.HiveSigner = HiveSigner;
