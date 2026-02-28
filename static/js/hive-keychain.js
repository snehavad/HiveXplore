/**
 * HiveKeychainHelper - A utility class to interact with the Hive Keychain browser extension
 * Provides methods to check if Keychain is installed, and to request various operations
 */

class HiveKeychainHelper {
	/**
	 * Check if Hive Keychain extension is installed and available
	 * @returns {boolean} True if Hive Keychain is available
	 */
	static isKeychainInstalled() {
		return typeof window.hive_keychain !== "undefined";
	}

	/**
	 * Request account information from Hive Keychain
	 * @param {string} username - Hive username
	 * @returns {Promise} Promise that resolves with keychain response
	 */
	static requestAccountInfo(username) {
		return new Promise((resolve, reject) => {
			if (!this.isKeychainInstalled()) {
				reject(new Error("Hive Keychain extension is not installed"));
				return;
			}

			window.hive_keychain.requestHandshake(() => {
				resolve({ success: true, message: "Keychain connected" });
			});
		});
	}

	/**
	 * Request a transfer operation via Hive Keychain
	 * @param {string} username - Sender's username
	 * @param {string} to - Recipient's username
	 * @param {string} amount - Amount to send (e.g. "1.000")
	 * @param {string} memo - Memo to include with transfer
	 * @param {string} currency - Currency to send (HIVE or HBD)
	 * @returns {Promise} Promise that resolves with keychain response
	 */
	static requestTransfer(username, to, amount, memo, currency) {
		return new Promise((resolve, reject) => {
			if (!this.isKeychainInstalled()) {
				reject(new Error("Hive Keychain extension is not installed"));
				return;
			}

			window.hive_keychain.requestTransfer(
				username,
				to,
				amount,
				memo,
				currency,
				(response) => {
					if (response.success) {
						resolve(response);
					} else {
						reject(new Error(response.message || "Unknown error"));
					}
				},
				true // Enforce account name validation
			);
		});
	}

	/**
	 * Request a vote operation via Hive Keychain
	 * @param {string} username - Voter's username
	 * @param {string} author - Post author
	 * @param {string} permlink - Post permlink
	 * @param {number} weight - Vote weight (-10000 to 10000)
	 * @returns {Promise} Promise that resolves with keychain response
	 */
	static requestVote(username, author, permlink, weight) {
		return new Promise((resolve, reject) => {
			if (!this.isKeychainInstalled()) {
				reject(new Error("Hive Keychain extension is not installed"));
				return;
			}

			window.hive_keychain.requestVote(
				username,
				permlink,
				author,
				weight,
				(response) => {
					if (response.success) {
						resolve(response);
					} else {
						reject(new Error(response.message || "Unknown error"));
					}
				}
			);
		});
	}

	/**
	 * Request a power up operation via Hive Keychain
	 * @param {string} username - Account username
	 * @param {string} to - Recipient username (usually same as username)
	 * @param {string} amount - Amount to power up
	 * @returns {Promise} Promise that resolves with keychain response
	 */
	static requestPowerUp(username, to, amount) {
		return new Promise((resolve, reject) => {
			if (!this.isKeychainInstalled()) {
				reject(new Error("Hive Keychain extension is not installed"));
				return;
			}

			window.hive_keychain.requestPowerUp(
				username,
				to,
				amount,
				(response) => {
					if (response.success) {
						resolve(response);
					} else {
						reject(new Error(response.message || "Unknown error"));
					}
				}
			);
		});
	}

	/**
	 * Request a power down operation via Hive Keychain
	 * @param {string} username - Account username
	 * @param {string} vestingShares - Amount of vesting shares to power down
	 * @returns {Promise} Promise that resolves with keychain response
	 */
	static requestPowerDown(username, vestingShares) {
		return new Promise((resolve, reject) => {
			if (!this.isKeychainInstalled()) {
				reject(new Error("Hive Keychain extension is not installed"));
				return;
			}

			window.hive_keychain.requestWithdrawVesting(
				username,
				vestingShares,
				(response) => {
					if (response.success) {
						resolve(response);
					} else {
						reject(new Error(response.message || "Unknown error"));
					}
				}
			);
		});
	}

	/**
	 * Verify Hive Keychain installation with visual feedback
	 * @returns {boolean} True if keychain is installed
	 * @param {boolean} showAlert - Whether to show an alert if keychain is not installed
	 */
	static verifyKeychainInstalled(showAlert = true) {
		const isInstalled = this.isKeychainInstalled();

		if (!isInstalled && showAlert) {
			alert(
				"Hive Keychain browser extension is required for this action.\n\nPlease install it from the Chrome Web Store or Firefox Add-ons store and reload the page."
			);
		}

		return isInstalled;
	}
}

// Initialize once the document is loaded
document.addEventListener("DOMContentLoaded", function () {
	// Check if Keychain is installed and update UI accordingly
	if (HiveKeychainHelper.isKeychainInstalled()) {
		// Hide any keychain warning messages if they exist
		const keychainAlert = document.getElementById("keychainAlert");
		if (keychainAlert) {
			keychainAlert.style.display = "none";
		}

		// Add a class to the body for CSS targeting
		document.body.classList.add("has-keychain");
	} else {
		// Show keychain warning if it exists
		const keychainAlert = document.getElementById("keychainAlert");
		if (keychainAlert) {
			keychainAlert.style.display = "block";
		}

		// Add a class to the body for CSS targeting
		document.body.classList.add("no-keychain");

		console.log(
			"Hive Keychain extension not detected. Some functionality will be limited."
		);
	}
});

// Make sure this is globally available
window.HiveKeychainHelper = HiveKeychainHelper;
