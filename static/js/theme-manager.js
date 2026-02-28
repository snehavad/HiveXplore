/**
 * Theme Manager for HiveBuzz
 * Manages theme colors and custom themes
 */
class ThemeManager {
	constructor() {
		this.customStyleElement = null;
		this.isInitialized = false;
		this.currentTheme = "blue";
		this.currentMode = "light";
		this.customColor = "#7367f0";

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
	 * Initialize theme manager
	 */
	initialize() {
		if (this.isInitialized) return;

		// Load current theme settings
		this.loadCurrentTheme();

		// Set up event handlers if on settings page
		if (document.getElementById("interface-settings-form")) {
			this.setupSettingsHandlers();
		}

		this.isInitialized = true;
		console.log("Theme Manager initialized");
	}

	/**
	 * Load current theme settings from body classes
	 */
	loadCurrentTheme() {
		// Detect current theme from body classes
		const body = document.body;
		this.currentMode = body.classList.contains("dark-mode")
			? "dark"
			: "light";

		// Check for theme classes
		const themeClasses = Array.from(body.classList).filter((cls) =>
			cls.startsWith("theme-")
		);
		if (themeClasses.length > 0) {
			this.currentTheme = themeClasses[0].replace("theme-", "");
		}

		// Look for custom color if using custom theme
		if (this.currentTheme === "custom") {
			const customStyleTag =
				document.getElementById("custom-theme-style");
			if (customStyleTag) {
				const colorMatch = customStyleTag.textContent.match(
					/--accent-primary: (#[0-9a-f]{6})/i
				);
				if (colorMatch && colorMatch[1]) {
					this.customColor = colorMatch[1];
				}
			}
		}
	}

	/**
	 * Setup handlers for the settings page
	 */
	setupSettingsHandlers() {
		// Theme color radio buttons
		document
			.querySelectorAll('input[name="theme_color"]')
			.forEach((radio) => {
				radio.addEventListener("change", () => {
					this.previewThemeChange(radio.value);
				});
			});

		// Custom color picker
		const customColorPicker = document.getElementById("customColorPicker");
		if (customColorPicker) {
			customColorPicker.addEventListener("input", () => {
				if (document.getElementById("colorCustom").checked) {
					this.previewCustomColor(customColorPicker.value);
				}
			});

			customColorPicker.addEventListener("click", () => {
				document.getElementById("colorCustom").checked = true;
				this.previewThemeChange("custom");
			});
		}

		// Dark mode toggle
		const darkModeSwitch = document.getElementById("darkModeSwitch");
		if (darkModeSwitch) {
			darkModeSwitch.addEventListener("change", () => {
				this.previewModeChange(darkModeSwitch.checked);
			});
		}
	}

	/**
	 * Preview a theme color change
	 * @param {string} theme - The theme name
	 */
	previewThemeChange(theme) {
		// Remove all theme classes
		document.body.classList.remove(
			"theme-blue",
			"theme-green",
			"theme-purple",
			"theme-orange",
			"theme-red",
			"theme-custom"
		);

		// Apply the selected theme
		if (theme === "custom") {
			document.body.classList.add("theme-custom");
			const customColor =
				document.getElementById("customColorPicker").value;
			this.previewCustomColor(customColor);
		} else {
			document.body.classList.add(`theme-${theme}`);
			// Remove any custom theme style if present
			if (this.customStyleElement) {
				this.customStyleElement.remove();
				this.customStyleElement = null;
			}
		}

		this.currentTheme = theme;
	}

	/**
	 * Preview a custom color
	 * @param {string} color - Hex color code
	 */
	previewCustomColor(color) {
		// Create or update custom style element
		if (!this.customStyleElement) {
			this.customStyleElement = document.createElement("style");
			this.customStyleElement.id = "custom-theme-style";
			document.head.appendChild(this.customStyleElement);
		}

		// Generate light/dark variants of the color
		const rgb = this.hexToRgb(color);
		const lightColor = this.lightenColor(color, 20);
		const darkColor = this.darkenColor(color, 20);

		// Create CSS Variables
		const css = `
            :root {
                --accent-primary: ${color};
                --accent-primary-rgb: ${rgb[0]}, ${rgb[1]}, ${rgb[2]};
                --accent-light: ${lightColor};
                --accent-dark: ${darkColor};
                --accent-outline: ${color}40;
            }
        `;

		this.customStyleElement.textContent = css;
		this.customColor = color;
	}

	/**
	 * Preview dark/light mode change
	 * @param {boolean} isDark - Whether to enable dark mode
	 */
	previewModeChange(isDark) {
		if (isDark) {
			document.body.classList.add("dark-mode");
			document.documentElement.classList.add("dark-mode");
		} else {
			document.body.classList.remove("dark-mode");
			document.documentElement.classList.remove("dark-mode");
		}

		this.currentMode = isDark ? "dark" : "light";

		// If custom theme is selected, re-apply the custom color to update light/dark variants
		if (this.currentTheme === "custom") {
			this.previewCustomColor(this.customColor);
		}
	}

	/**
	 * Convert hex color to RGB
	 * @param {string} hex - Hex color code
	 * @returns {number[]} RGB values array
	 */
	hexToRgb(hex) {
		// Remove # if present
		hex = hex.replace("#", "");

		// Convert to RGB
		return [
			parseInt(hex.substring(0, 2), 16),
			parseInt(hex.substring(2, 4), 16),
			parseInt(hex.substring(4, 6), 16),
		];
	}

	/**
	 * Lighten a color by percentage
	 * @param {string} hex - Hex color code
	 * @param {number} percent - Percentage to lighten (0-100)
	 * @returns {string} Lightened color in hex
	 */
	lightenColor(hex, percent) {
		const rgb = this.hexToRgb(hex);
		const new_rgb = rgb.map((val) => {
			return Math.min(
				255,
				Math.floor(val + (255 - val) * (percent / 100))
			);
		});
		return this.rgbToHex(new_rgb);
	}

	/**
	 * Darken a color by percentage
	 * @param {string} hex - Hex color code
	 * @param {number} percent - Percentage to darken (0-100)
	 * @returns {string} Darkened color in hex
	 */
	darkenColor(hex, percent) {
		const rgb = this.hexToRgb(hex);
		const new_rgb = rgb.map((val) => {
			return Math.max(0, Math.floor(val * (1 - percent / 100)));
		});
		return this.rgbToHex(new_rgb);
	}

	/**
	 * Convert RGB array to hex color
	 * @param {number[]} rgb - RGB values array
	 * @returns {string} Hex color code
	 */
	rgbToHex(rgb) {
		return (
			"#" +
			rgb
				.map((x) => {
					const hex = x.toString(16);
					return hex.length === 1 ? "0" + hex : hex;
				})
				.join("")
		);
	}
}

// Initialize ThemeManager
const themeManager = new ThemeManager();

// Make it globally available
window.themeManager = themeManager;
