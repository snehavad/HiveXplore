document.addEventListener("DOMContentLoaded", function () {
	// Set current year in footer
	const yearElement = document.querySelector(".site-footer p");
	if (yearElement) {
		const currentYear = new Date().getFullYear();
		yearElement.innerHTML = yearElement.innerHTML.replace(
			"{{ now.year }}",
			currentYear
		);
	}

	// Check if Hive Keychain is installed
	if (typeof window.hive_keychain === "undefined") {
		const keychainBtn = document.getElementById("keychain-login-btn");
		if (keychainBtn) {
			keychainBtn.disabled = true;
			keychainBtn.textContent = "Hive Keychain Not Found";

			// Add info notification
			const infoText = document.querySelector(".info-text");
			if (infoText) {
				infoText.innerHTML =
					'<strong>Hive Keychain not detected!</strong> Please install the <a href="https://chrome.google.com/webstore/detail/hive-keychain/jcacnejopjdphbnjgfaaobbfafkihpep" target="_blank">Hive Keychain browser extension</a> to continue.';
				infoText.style.color = "#f44336";
			}
		}
	}

	// Post creation with Keychain
	const publishBtn = document.getElementById("publish-btn");
	if (publishBtn && window.hive_keychain) {
		publishBtn.addEventListener("click", function () {
			const title = document.getElementById("title").value;
			const body = document.getElementById("body").value;
			const tagsInput = document.getElementById("tags").value;
			const username = document.getElementById("author-username").value;

			if (!title || !body) {
				alert("Title and content are required.");
				return;
			}

			// Process tags
			let tags = tagsInput
				.split(",")
				.map((tag) => tag.trim().toLowerCase());
			tags = tags.filter((tag) => tag);
			if (tags.length === 0) {
				tags = ["hivebuzz"]; // Default tag
			}

			// Generate permlink
			const permlink = generateRandomPermlink();

			// For the hackathon demo, we'll just submit the form instead of actual blockchain posting
			if (
				confirm(
					"In a real implementation, this would broadcast to the Hive blockchain. Continue with demo submission?"
				)
			) {
				document.getElementById("post-form").submit();
			}
		});
	}

	// Flash message handling with auto-dismiss
	const flashMessages = document.querySelectorAll(".flash-message");
	flashMessages.forEach((message) => {
		setTimeout(() => {
			message.style.opacity = "0";
			setTimeout(() => {
				message.style.display = "none";
			}, 500);
		}, 5000);
	});
});

// Utility functions
function generateRandomPermlink() {
	const chars = "abcdefghijklmnopqrstuvwxyz0123456789";
	const length = 16;
	let result = "";
	for (let i = 0; i < length; i++) {
		result += chars.charAt(Math.floor(Math.random() * chars.length));
	}
	return result;
}
