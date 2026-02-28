class HiveAuth {
	constructor(options = {}) {
		this.authEndpoint = options.authEndpoint || "https://hiveauth.com/api/";
		this.client = options.client || "hivebuzz";
		this.challenge = options.challenge || this.generateUUID();
		this.key = options.key || this.generateUUID();
		this.ws = null;

		// Add CORS proxy if needed for local development
		this.useProxy = options.useProxy || false;
		this.corsProxy =
			options.corsProxy || "https://cors-anywhere.herokuapp.com/";
	}

	generateUUID() {
		return "xxxxxxxx-xxxx-4xxx-Xxxx-xxxxxxxxxxxx".replace(
			/[xy]/g,
			function (c) {
				const r = (Math.random() * 16) | 0,
					v = c === "x" ? r : (r & 0x3) | 0x8;
				return v.toString(16);
			}
		);
	}

	async getAuthData() {
		try {
			const url = `${this.authEndpoint}auth_data?client=${this.client}&challenge=${this.challenge}&key=${this.key}`;
			const fetchUrl = this.useProxy ? `${this.corsProxy}${url}` : url;

			console.log("Fetching auth data from:", fetchUrl);

			const response = await fetch(fetchUrl, {
				method: "GET",
				headers: {
					Accept: "application/json",
					"Content-Type": "application/json",
				},
			});

			if (!response.ok) {
				console.error(
					"HTTP error:",
					response.status,
					response.statusText
				);
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			return await response.json();
		} catch (error) {
			console.error("Error getting auth data:", error);
			throw error;
		}
	}

	async getToken(username) {
		try {
			const url = `${this.authEndpoint}get_token?username=${username}&client=${this.client}&challenge=${this.challenge}&key=${this.key}`;
			const fetchUrl = this.useProxy ? `${this.corsProxy}${url}` : url;

			console.log("Getting token from:", fetchUrl);

			const response = await fetch(fetchUrl, {
				method: "GET",
				headers: {
					Accept: "application/json",
					"Content-Type": "application/json",
				},
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			return await response.json();
		} catch (error) {
			console.error("Error getting token:", error);
			throw error;
		}
	}

	connectWebSocket(authData, callback) {
		if (this.ws) this.ws.close();

		console.log("Connecting to WebSocket with auth data:", authData);

		this.ws = new WebSocket("wss://hiveauth.com/ws/");

		this.ws.onopen = () => {
			console.log("WebSocket connection opened");
			this.ws.send(
				JSON.stringify({
					cmd: "register",
					uuid: authData.uuid,
					key: this.key,
				})
			);
		};

		this.ws.onmessage = (event) => {
			try {
				const data = JSON.parse(event.data);
				console.log("WebSocket message received:", data);

				if (data.cmd === "auth_wait") {
					// Waiting for user to approve
					console.log("Waiting for user authentication...");
				} else if (data.cmd === "auth_ack") {
					// Authentication successful
					console.log("Authentication successful!");
					callback(true, data.username, data);
					this.ws.close();
				} else if (data.cmd === "auth_nack") {
					// Authentication failed/rejected
					console.log("Authentication rejected!");
					callback(false, null, data);
					this.ws.close();
				}
			} catch (error) {
				console.error("Error handling WebSocket message:", error);
				callback(false, null, { error: error.message });
			}
		};

		this.ws.onerror = (error) => {
			console.error("WebSocket error:", error);
			callback(false, null, { error: "WebSocket connection failed" });
		};

		this.ws.onclose = () => {
			console.log("WebSocket connection closed");
		};
	}

	// Mock method for testing without actual API calls
	mockAuthentication(username) {
		console.log("Using mock authentication for testing");

		const mockAuthData = {
			uuid: this.generateUUID(),
			login_url:
				"https://hivesigner.com/oauth2/authorize?client_id=test&redirect_uri=https://example.com",
		};

		const mockTokenResponse = {
			token: "mock_token_" + Date.now(),
		};

		setTimeout(() => {
			console.log("Mock authentication successful");
			return {
				authData: mockAuthData,
				tokenResponse: mockTokenResponse,
			};
		}, 1000);
	}
}

// Initialize HiveAuth functionality when document is ready
document.addEventListener("DOMContentLoaded", function () {
	const hiveauthLoginBtn = document.getElementById("hiveauth-login-btn");

	if (hiveauthLoginBtn) {
		hiveauthLoginBtn.addEventListener("click", async function () {
			const username = document.getElementById("hiveauth-username").value;
			if (!username) {
				alert("Please enter your username");
				return;
			}

			const loadingIndicator =
				document.getElementById("hiveauth-loading");
			if (loadingIndicator) loadingIndicator.style.display = "block";

			try {
				// Use useProxy: true for local development to bypass CORS issues
				const hiveAuth = new HiveAuth({
					client: "hivebuzz",
					useProxy: true,
				});

				// Get auth data from HiveAuth service
				let authData;
				try {
					authData = await hiveAuth.getAuthData();
					console.log("Auth data:", authData);
				} catch (error) {
					console.error("Error getting auth data:", error);
					alert(
						"Error connecting to HiveAuth. Please try again later."
					);
					if (loadingIndicator)
						loadingIndicator.style.display = "none";
					return;
				}

				// Show QR code container
				const qrContainer = document.getElementById("qrcode-container");
				if (qrContainer) qrContainer.style.display = "block";

				// Generate QR code
				const qrcodeElement =
					document.getElementById("hiveauth-qrcode");
				if (qrcodeElement) {
					qrcodeElement.innerHTML = "";
					try {
						await QRCode.toCanvas(
							qrcodeElement,
							authData.login_url,
							{
								width: 200,
								margin: 1,
							}
						);
					} catch (error) {
						console.error("Error generating QR code:", error);
						qrcodeElement.innerText =
							"Error generating QR code. Please use the HiveAuth app and enter this code: " +
							authData.uuid;
					}
				}

				// Get token
				let tokenResponse;
				try {
					tokenResponse = await hiveAuth.getToken(username);
					console.log("Token response:", tokenResponse);
				} catch (error) {
					console.error("Error getting token:", error);
					alert(
						"Error getting authentication token. Please try again."
					);
					if (loadingIndicator)
						loadingIndicator.style.display = "none";
					if (qrContainer) qrContainer.style.display = "none";
					return;
				}

				// Connect WebSocket to wait for authentication
				hiveAuth.connectWebSocket(
					authData,
					function (success, authenticatedUser, data) {
						if (loadingIndicator)
							loadingIndicator.style.display = "none";

						if (success && authenticatedUser) {
							// Create hidden form to submit data to server
							const form = document.createElement("form");
							form.method = "POST";
							form.action = "/login-hiveauth";

							const usernameInput =
								document.createElement("input");
							usernameInput.type = "hidden";
							usernameInput.name = "username";
							usernameInput.value = authenticatedUser;

							const tokenInput = document.createElement("input");
							tokenInput.type = "hidden";
							tokenInput.name = "auth_token";
							tokenInput.value = tokenResponse.token;

							const uuidInput = document.createElement("input");
							uuidInput.type = "hidden";
							uuidInput.name = "uuid";
							uuidInput.value = authData.uuid;

							form.appendChild(usernameInput);
							form.appendChild(tokenInput);
							form.appendChild(uuidInput);

							document.body.appendChild(form);
							form.submit();
						} else {
							alert(
								"Authentication failed or was canceled. Please try again."
							);
							if (qrContainer) qrContainer.style.display = "none";
						}
					}
				);
			} catch (error) {
				console.error("HiveAuth error:", error);
				alert("HiveAuth error: " + error.message);
				if (loadingIndicator) loadingIndicator.style.display = "none";
			}
		});
	}
});

/**
 * HiveAuth helper for integrating with the HiveAuth mobile app authentication
 */
const HiveAuthHelper = {
    /**
     * Initialize HiveAuth and setup auth data
     * @param {string} username - Hive username
     * @param {string} appName - Application name to show in HiveAuth
     * @returns {Object} Authentication data including token, uuid, and QR info
     */
    initAuth: function(username, appName = "HiveBuzz") {
        // Generate random tokens
        const token = this.generateRandomString(16);
        const uuid = this.generateUUID();

        // Create auth data object
        const authData = {
            username,
            token,
            uuid,
            app: appName,
            challenge: `Login to ${appName}: ${token}`
        };

        // Convert to base64 for QR code
        const authString = btoa(JSON.stringify(authData));
        const authUrl = `hiveauth://login/${authString}`;

        return {
            username,
            token,
            uuid,
            authString,
            authUrl
        };
    },

    /**
     * Generate QR code for HiveAuth
     * @param {HTMLElement} element - Element to render QR code in
     * @param {string} authUrl - HiveAuth URL for QR
     * @param {Object} options - QRCode options
     * @returns {Promise} Resolves when QR code is generated
     */
    generateQRCode: function(element, authUrl, options = { width: 200 }) {
        return new Promise((resolve, reject) => {
            if (!window.QRCode) {
                return reject("QRCode library not loaded");
            }

            QRCode.toCanvas(element, authUrl, options, function(error) {
                if (error) {
                    reject(error);
                } else {
                    resolve();
                }
            });
        });
    },

    /**
     * Check authentication status from server
     * @param {string} username - Hive username
     * @param {string} token - Authentication token
     * @param {string} uuid - Authentication UUID
     * @returns {Promise} Authentication status check result
     */
    checkAuthStatus: function(username, token, uuid) {
        const params = new URLSearchParams({
            username,
            auth_token: token,
            uuid
        });

        return fetch(`/api/check-hiveauth?${params.toString()}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            });
    },

    /**
     * Start polling for authentication status
     * @param {string} username - Hive username
     * @param {string} token - Authentication token
     * @param {string} uuid - Authentication UUID
     * @param {function} onSuccess - Callback when authentication succeeds
     * @param {function} onTimeout - Callback when authentication times out
     * @param {number} interval - Polling interval in ms
     * @param {number} timeout - Timeout in ms
     */
    pollForAuth: function(username, token, uuid, onSuccess, onTimeout, interval = 2000, timeout = 120000) {
        const startTime = Date.now();
        const checkInterval = setInterval(() => {
            // Check if we've timed out
            if (Date.now() - startTime > timeout) {
                clearInterval(checkInterval);
                if (onTimeout) onTimeout();
                return;
            }

            // Check auth status
            this.checkAuthStatus(username, token, uuid)
                .then(data => {
                    if (data.authenticated) {
                        clearInterval(checkInterval);
                        if (onSuccess) onSuccess(data);
                    }
                })
                .catch(error => console.error("Auth check error:", error));
        }, interval);

        // Return the interval ID so it can be cleared if needed
        return checkInterval;
    },

    /**
     * Generate a random string for tokens
     * @param {number} length - Length of string to generate
     * @returns {string} Random string
     */
    generateRandomString: function(length = 16) {
        return Math.random().toString(36).substring(2, 2 + length);
    },

    /**
     * Generate a UUID v4
     * @returns {string} UUID
     */
    generateUUID: function() {
        return 'xxxxxxxx-xxxx-4xxx-Xxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }
};

// Make it globally available
window.HiveAuthHelper = HiveAuthHelper;
