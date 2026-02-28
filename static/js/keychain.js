document.addEventListener("DOMContentLoaded", function () {
	// Function to check if Hive Keychain is installed
	function checkForKeychain() {
		const keychainInstalled = window.hive_keychain || false;
		const keychainNoticeDiv = document.getElementById("keychain-status");
		const keychainLoginBtn = document.getElementById("keychain-login-btn");

		console.log(
			"Checking for Hive Keychain:",
			keychainInstalled ? "Found" : "Not found"
		);

		if (!keychainInstalled) {
			if (keychainNoticeDiv) {
				keychainNoticeDiv.innerHTML =
					"<strong>Hive Keychain not detected!</strong> Please install the <a href='https://chrome.google.com/webstore/detail/hive-keychain/jcacnejopjdphbnjgfaaobbfafkihpep' target='_blank'>Hive Keychain browser extension</a> to continue.";
				keychainNoticeDiv.classList.remove("alert-info");
				keychainNoticeDiv.classList.add("alert-danger");
			}
			if (keychainLoginBtn) {
				keychainLoginBtn.disabled = true;
			}
		} else {
			if (keychainNoticeDiv) {
				keychainNoticeDiv.textContent = "Hive Keychain detected!";
				keychainNoticeDiv.classList.remove("alert-info");
				keychainNoticeDiv.classList.add("alert-success");
			}
			if (keychainLoginBtn) {
				keychainLoginBtn.disabled = false;
			}
		}

		return keychainInstalled;
	}

	// Function to handle Hive Keychain login
	function loginWithKeychain() {
		const username = document.getElementById("keychain-username").value;
		if (!username) {
			alert("Please enter your Hive username");
			return;
		}

		console.log(
			"Attempting to login with Hive Keychain for user:",
			username
		);

		// Generate a random string as challenge for the signature
		const challenge =
			"hivebuzz-auth-" + Math.random().toString(36).substring(2, 15);

		// Request signature from Hive Keychain
		if (window.hive_keychain) {
			window.hive_keychain.requestSignBuffer(
				username,
				`Login to HiveBuzz: ${challenge}`,
				"Posting",
				(response) => {
					console.log("Keychain response:", response);

					if (response.success) {
						// Populate and submit the form
						document.getElementById("keychain_username").value =
							username;
						document.getElementById("keychain_signature").value =
							response.result;
						document.getElementById("keychain_challenge").value =
							challenge;
						document.getElementById("keychainLoginForm").submit();
					} else {
						alert(
							`Error: ${
								response.message ||
								"Could not sign with Keychain"
							}`
						);
					}
				}
			);
		} else {
			alert("Hive Keychain extension is required for this login method.");
		}
	}

	// Check if Keychain exists on page load
	setTimeout(checkForKeychain, 500); // Give a slight delay for Keychain to initialize

	// Set up event listener for the login button
	const keychainLoginBtn = document.getElementById("keychain-login-btn");
	if (keychainLoginBtn) {
		keychainLoginBtn.addEventListener("click", function () {
			if (checkForKeychain()) {
				loginWithKeychain();
			} else {
				alert(
					"Hive Keychain not found. Please install the extension first."
				);
			}
		});
	}
});
