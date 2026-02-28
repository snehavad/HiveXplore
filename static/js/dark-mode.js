/**
 * Dark Mode Manager for HiveBuzz
 * Manages dark/light theme preferences and applies them consistently
 */
class DarkModeManager {
	constructor() {
		this.darkModeToggle = document.getElementById("themeToggle");
		this.body = document.body;
		this.isInitialized = false;

		// Initialize when DOM is ready
		if (document.readyState === "loading") {
			document.addEventListener("DOMContentLoaded", () =>
				this.initialize()
			);
		} else {
			this.initialize();
		}
	}

	/**
	 * Initialize the dark mode system
	 */
	initialize() {
		if (this.isInitialized) return;

		// Check for saved theme preference or use system preference
		this.loadThemePreference();

		// Set up listeners for theme toggle
		this.setupEventListeners();

		// Apply color theme based on current settings
		this.applyCurrentTheme();

		this.isInitialized = true;
		console.log("Dark Mode Manager initialized");
	}

	/**
	 * Load theme preference from local storage or system preference
	 */
	loadThemePreference() {
		const savedTheme = localStorage.getItem("theme");

		if (this.darkModeToggle) {
			if (savedTheme === "dark") {
				this.body.classList.add("dark-mode");
				this.darkModeToggle.checked = true;
			} else if (savedTheme === "light") {
				this.body.classList.remove("dark-mode");
				this.darkModeToggle.checked = false;
			} else if (
				window.matchMedia &&
				window.matchMedia("(prefers-color-scheme: dark)").matches
			) {
				// Use system preference if no saved preference
				this.body.classList.add("dark-mode");
				this.darkModeToggle.checked = true;
				localStorage.setItem("theme", "dark");
			}
		} else {
			// If toggle doesn't exist, just check local storage or system preference
			if (
				savedTheme === "dark" ||
				(savedTheme !== "light" &&
					window.matchMedia &&
					window.matchMedia("(prefers-color-scheme: dark)").matches)
			) {
				this.body.classList.add("dark-mode");
			}
		}
	}

	/**
	 * Set up event listeners for the dark mode toggle
	 */
	setupEventListeners() {
		if (this.darkModeToggle) {
			this.darkModeToggle.addEventListener("change", () => {
				this.toggleDarkMode(this.darkModeToggle.checked);
			});
		}

		// Listen for system preference changes
		if (window.matchMedia) {
			const mediaQuery = window.matchMedia(
				"(prefers-color-scheme: dark)"
			);
			mediaQuery.addEventListener("change", (e) => {
				// Only apply if user hasn't explicitly set a preference
				if (!localStorage.getItem("theme")) {
					this.toggleDarkMode(e.matches);
				}
			});
		}
	}

	/**
	 * Toggle between dark and light mode
	 * @param {boolean} enableDark - Whether to enable dark mode
	 */
	toggleDarkMode(enableDark) {
		if (enableDark) {
			this.body.classList.add("dark-mode");
			document.documentElement.classList.add("dark-mode");
			localStorage.setItem("theme", "dark");
		} else {
			this.body.classList.remove("dark-mode");
			document.documentElement.classList.remove("dark-mode");
			localStorage.setItem("theme", "light");
		}

		// Update the theme icon
		this.updateThemeIcon(enableDark);

		// Apply specific styles to components
		this.applyComponentSpecificStyles(enableDark);

		// Save user preference if logged in
		this.saveUserPreference("dark_mode", enableDark);
	}

	/**
	 * Update the theme icon based on the current mode
	 * @param {boolean} isDark - Whether dark mode is enabled
	 */
	updateThemeIcon(isDark) {
		const icon = document.querySelector('[data-theme-icon="theme-toggle"]');
		if (icon) {
			if (isDark) {
				icon.classList.remove("bi-moon");
				icon.classList.add("bi-sun");
			} else {
				icon.classList.remove("bi-sun");
				icon.classList.add("bi-moon");
			}
		}
	}

	/**
	 * Apply specific styles to components that need special handling in dark mode
	 * @param {boolean} isDark - Whether dark mode is enabled
	 */
	applyComponentSpecificStyles(isDark) {
		// Handle tables
		document.querySelectorAll(".table").forEach((table) => {
			if (isDark) {
				table.classList.add("table-dark");
			} else {
				table.classList.remove("table-dark");
			}
		});

		// Handle navbar
		document.querySelectorAll(".navbar").forEach((navbar) => {
			if (isDark) {
				navbar.classList.add("navbar-dark");
				navbar.classList.remove("navbar-light");
			} else {
				navbar.classList.add("navbar-light");
				navbar.classList.remove("navbar-dark");
			}
		});

		// Handle form inputs for better contrast
		document
			.querySelectorAll("input, textarea, select")
			.forEach((input) => {
				if (isDark) {
					input.dataset.darkMode = "true";
				} else {
					delete input.dataset.darkMode;
				}
			});
	}

	/**
	 * Apply current theme settings to all components
	 */
	applyCurrentTheme() {
		const isDark = this.body.classList.contains("dark-mode");
		this.applyComponentSpecificStyles(isDark);
	}

	/**
	 * Save user preference to server if user is logged in
	 * @param {string} key - Preference key
	 * @param {any} value - Preference value
	 */
	saveUserPreference(key, value) {
		const username = this.getUsernameFromPage();
		if (!username) return;

		// Create a properly structured object
		const preferenceData = {};
		preferenceData[key] = value;

		fetch("/api/user/preferences", {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify(preferenceData),
		})
			.then((response) => {
				if (!response.ok) {
					throw new Error("Network response was not ok");
				}
				return response.json();
			})
			.then((data) => {
				console.log("Preference saved successfully:", data);
			})
			.catch((error) => {
				console.error("Error saving preference:", error);
			});
	}

	/**
	 * Get username from page if user is logged in
	 * @returns {string|null} Username or null if not logged in
	 */
	getUsernameFromPage() {
		// Try to get username from various page elements
		const userDropdown = document.getElementById("userDropdown");
		if (userDropdown && userDropdown.textContent) {
			const username = userDropdown.textContent.trim().replace("@", "");
			if (username) return username;
		}

		// Try to get from meta tag if available
		const usernameMeta = document.querySelector(
			'meta[name="current-user"]'
		);
		return usernameMeta ? usernameMeta.getAttribute("content") : null;
	}
}

// Initialize when DOM is ready
const darkModeManager = new DarkModeManager();

// Make it globally available
window.darkModeManager = darkModeManager;
